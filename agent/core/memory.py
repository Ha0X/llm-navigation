import json
import time
from pathlib import Path
from agent.core.llm import chat

class MemoryStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ep_path = self.root / 'episodic.jsonl'
        self.sem_path = self.root / 'semantic.json'
        self.proc_path = self.root / 'procedural.json'
        if not self.ep_path.exists():
            self.ep_path.write_text('', encoding='utf-8')
        if not self.sem_path.exists():
            self.sem_path.write_text(json.dumps({"aliases":{},"obstacles":[],"high_cost_zones":[],"time_windows":[],"dynamic_blocks":[]}, ensure_ascii=False), encoding='utf-8')
        if not self.proc_path.exists():
            self.proc_path.write_text(json.dumps({"skills":{}}, ensure_ascii=False), encoding='utf-8')
        self.semantic = json.loads(self.sem_path.read_text(encoding='utf-8'))
        if 'dynamic_blocks' not in self.semantic:
            self.semantic['dynamic_blocks'] = []
        self.procedural = json.loads(self.proc_path.read_text(encoding='utf-8'))

    def append_episodic(self, record: dict):
        record['ts'] = record.get('ts') or int(time.time())
        with self.ep_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def save(self):
        self.sem_path.write_text(json.dumps(self.semantic, ensure_ascii=False, indent=2), encoding='utf-8')
        self.proc_path.write_text(json.dumps(self.procedural, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_episodic(self):
        items = []
        with self.ep_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        return items

    def retrieve(self, task_text: str, locations: dict, k: int = 5):
        episodes = self._load_episodic()
        now = int(time.time())
        def score(e):
            recency = max(0, 1.0 - (now - int(e.get('ts', now))) / 86400.0)
            tag = 0.0
            place = e.get('place')
            for p in locations.get('places', []):
                if p.get('name') == place:
                    tag = 1.0
                    break
            fail_penalty = 0.5 if e.get('result') in ('blocked','fail') else 0.0
            return recency * 0.6 + tag * 0.3 - fail_penalty * 0.4
        episodes.sort(key=score, reverse=True)
        top = episodes[:k]
        ctx = {
            'episodes': top,
            'semantic': self.semantic,
            'procedural': self.procedural
        }
        return ctx

    def reflect(self, logs: list):
        fail_tips = []
        for l in logs:
            if l.get('type') == 'navigate' and l.get('result') == 'blocked':
                fail_tips.append('prefer_alt_route')
        if fail_tips:
            skills = self.procedural.get('skills', {})
            nav = skills.get('navigate', {'success':0,'fail':0,'avg_time':0.0,'tips':[]})
            nav['tips'] = list(set(nav.get('tips', []) + fail_tips))
            skills['navigate'] = nav
            self.procedural['skills'] = skills
        tip_line = None
        try:
            content = chat(
                system='你是机器人自反思模块。根据执行日志总结一句"下次应怎样"的建议，要求精炼且具体。',
                user=json.dumps({'logs': logs}, ensure_ascii=False),
                max_tokens=60
            )
            if content:
                tip_line = content.strip().split('\n')[0]
        except Exception:
            tip_line = None
        if tip_line:
            skills = self.procedural.get('skills', {})
            nav = skills.get('navigate', {'success':0,'fail':0,'avg_time':0.0,'tips':[]})
            if tip_line not in nav.get('tips', []):
                nav['tips'] = nav.get('tips', []) + [tip_line]
            skills['navigate'] = nav
            self.procedural['skills'] = skills
        now = int(time.time())
        ttl_sec = 3600
        dyn = self.semantic.get('dynamic_blocks', [])
        active = []
        for l in logs:
            if l.get('type') == 'navigate' and l.get('result') == 'blocked':
                reason = l.get('reason','dynamic')
                if reason == 'dynamic':
                    pos = l.get('pos')
                    if pos:
                        key = (int(pos[0]), int(pos[1]))
                        found = None
                        for o in dyn:
                            if int(o.get('x')) == key[0] and int(o.get('y')) == key[1]:
                                found = o
                                break
                        if found:
                            conf = float(found.get('confidence', 0.5))
                            conf = min(0.99, conf * 0.8 + 0.2)
                            found['confidence'] = conf
                            found['ts'] = now
                            found['expire_ts'] = now + ttl_sec
                            active.append(found)
                        else:
                            o = {'x': key[0], 'y': key[1], 'label': 'dynamic', 'ts': now, 'expire_ts': now + ttl_sec, 'confidence': 0.6}
                            dyn.append(o)
                            active.append(o)
        dyn = [o for o in dyn if int(o.get('expire_ts', 0)) > now]
        self.semantic['dynamic_blocks'] = dyn
        self.semantic['obstacles'] = [o for o in self.semantic.get('obstacles', []) if o.get('label') == 'pillar']
        skills = self.procedural.get('skills', {})
        nav = skills.get('navigate', {'success':0,'fail':0,'avg_time':0.0,'tips':[]})
        stats = nav.get('stats', {})
        decay = 0.85
        places_attempts = {}
        places_blocked = {}
        for l in logs:
            if l.get('type') == 'navigate':
                name = l.get('target')
                places_attempts[name] = places_attempts.get(name, 0) + 1
                if l.get('result') == 'blocked' and l.get('reason','dynamic') == 'dynamic':
                    places_blocked[name] = places_blocked.get(name, 0) + 1
        for name, s in list(stats.items()):
            att = float(s.get('attempts', 0)) * decay
            blk = float(s.get('blocked', 0)) * decay
            stats[name] = {'attempts': att, 'blocked': blk, 'prob': (blk / att) if att > 0 else 0.0}
        for name, att_add in places_attempts.items():
            prev = stats.get(name, {'attempts':0.0,'blocked':0.0,'prob':0.0})
            blk_add = float(places_blocked.get(name, 0))
            att = prev['attempts'] + float(att_add)
            blk = prev['blocked'] + blk_add
            stats[name] = {'attempts': att, 'blocked': blk, 'prob': (blk / att) if att > 0 else 0.0}
        nav['stats'] = stats
        skills['navigate'] = nav
        self.procedural['skills'] = skills
        self.save()
        return {'tips': list(set(fail_tips + ([tip_line] if tip_line else []))), 'new_dynamic_blocks': active}

class NoOpMemory(MemoryStore):
    def __init__(self, root: Path):
        super().__init__(root)
    def append_episodic(self, record: dict):
        pass
    def reflect(self, logs: list):
        return {'tips': [], 'new_obstacles': []}
