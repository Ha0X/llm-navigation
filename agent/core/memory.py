import json
import time
from pathlib import Path

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
            self.sem_path.write_text(json.dumps({"aliases":{},"obstacles":[],"high_cost_zones":[],"time_windows":[]}, ensure_ascii=False), encoding='utf-8')
        if not self.proc_path.exists():
            self.proc_path.write_text(json.dumps({"skills":{}}, ensure_ascii=False), encoding='utf-8')
        self.semantic = json.loads(self.sem_path.read_text(encoding='utf-8'))
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
        obstacles = []
        for l in logs:
            if l.get('type') == 'navigate' and l.get('result') == 'blocked':
                pos = l.get('pos')
                if pos:
                    obstacles.append({'x':pos[0],'y':pos[1],'label':'dynamic_block'})
        if obstacles:
            self.semantic['obstacles'] = list(self.semantic.get('obstacles', [])) + obstacles
        self.save()
        return {'tips': fail_tips, 'new_obstacles': obstacles}
