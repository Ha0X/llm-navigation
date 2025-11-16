import re
import json
from typing import List, Dict, Any
from agent.core.llm import json_response

class Planner:
    def plan(self, task_text: str, memory_ctx: Dict[str, Any], locations: Dict[str, Any], config: Dict[str, Any]):
        llm_out = json_response(
            system="你是一个机器人任务规划器。严格返回JSON，不要解释。必须：1) 显式体现时间窗（例如 08:00-09:00 避免 corridor）；2) 体现优先级（battery_zone、tools 优先）；3) 当遇设备占用/连续阻塞时，给出拍相邻点的 fallback；4) rationale 需解释时间窗、优先级与fallback；",
            user=json.dumps({
                "task": task_text,
                "locations": [p['name'] for p in locations.get('places', [])],
                "location_tags": {p['name']: p.get('tags', []) for p in locations.get('places', [])},
                "memory_tips": memory_ctx.get('procedural', {}).get('skills', {}).get('navigate', {}).get('tips', []),
                "semantic": memory_ctx.get('semantic', {}),
                "constraints": self._extract_constraints(task_text)
            }, ensure_ascii=False),
            schema_hint='返回形如{"order":["A","B"],"steps":[{"type":"navigate","target":"A"},{"type":"inspect","target":"A"},{"type":"wait","duration":10,"reason":"08:00-09:00 避免 corridor"},{"type":"navigate_alt","target":"B","reason":"避开拥堵"},{"type":"inspect_or_adjacent","target":"B"}],"milestones":[{"name":"到达A","eta_min":5}],"notes":[],"rationale":"解释时间窗/优先级/绕行与fallback","errors":["约束冲突解释或不可达原因"]}'
        )
        if not llm_out or not isinstance(llm_out, dict):
            raise ValueError('LLM planning failed')
        order = llm_out.get('order')
        steps = llm_out.get('steps')
        milestones = llm_out.get('milestones', [])
        notes = llm_out.get('notes', [])
        rationale = llm_out.get('rationale')
        errors = llm_out.get('errors', [])
        if not steps:
            raise ValueError('LLM planning returned empty steps')
        plan = {
            'task': task_text,
            'order': order,
            'steps': steps,
            'milestones': milestones,
            'notes': notes,
            'rationale': rationale,
            'errors': errors,
            'constraints': self._extract_constraints(task_text)
        }
        plan = self._augment_with_constraints(plan, locations)
        return plan

    def _extract_order(self, task_text: str, locations: Dict[str, Any]) -> List[str]:
        arrow = re.split(r'\s*(?:→|->|-)\s*', task_text)
        names = [s.strip() for s in arrow if re.fullmatch(r'[A-Z]', s.strip())]
        tokens = re.findall(r'([A-Z])', task_text)
        if names or tokens:
            seen = set()
            ordered = []
            for s in names:
                if s not in seen:
                    seen.add(s)
                    ordered.append(s)
            for t in tokens:
                if t not in seen:
                    seen.add(t)
                    ordered.append(t)
            if ordered:
                return ordered
        return [p['name'] for p in locations.get('places', [])]

    def _extract_constraints(self, task_text: str) -> Dict[str, Any]:
        m = re.search(r'(\d+)分钟', task_text)
        deadline = int(m.group(1)) if m else None
        tw = None
        m2 = re.search(r'(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})', task_text)
        if m2:
            tw = {'start': m2.group(1), 'end': m2.group(2), 'avoid_tags': ['corridor']}
        pr_tags = []
        if 'battery_zone' in task_text:
            pr_tags.append('battery_zone')
        if 'tools' in task_text:
            pr_tags.append('tools')
        return {'deadline_minutes': deadline, 'time_window': tw, 'priority_tags': pr_tags}

    def _apply_priority(self, task_text: str, order: List[str]) -> List[str]:
        m = re.search(r'优先([A-Z])', task_text)
        if not m or not order:
            return order
        p = m.group(1)
        if p in order:
            new = [p] + [x for x in order if x != p]
            return new
        return order

    def _augment_with_constraints(self, plan: Dict[str, Any], locations: Dict[str, Any]) -> Dict[str, Any]:
        cons = plan.get('constraints', {})
        tw = cons.get('time_window')
        order = plan.get('order') or []
        steps = plan.get('steps') or []
        name_to_tags = {p['name']: p.get('tags', []) for p in locations.get('places', [])}
        existing_targets = [s.get('target') for s in steps if 'target' in s]
        new_steps = []
        # 1) Ensure priority places are included with navigate + inspect
        pr_tags = cons.get('priority_tags') or []
        pr_places = [n for n, tags in name_to_tags.items() if any(t in tags for t in pr_tags)]
        for n in pr_places:
            if n not in existing_targets:
                new_steps.append({'type':'navigate','target': n})
                new_steps.append({'type':'inspect','target': n})
        # Append original steps
        for s in steps:
            new_steps.append(s)
            if s.get('type') == 'navigate' and s.get('target') in name_to_tags:
                tags = name_to_tags[s['target']]
                if tw and 'corridor' in tags:
                    new_steps.append({'type':'note','text':'08:00-09:00 避免 corridor，必要时等待或改用替代路径'})
                    new_steps.append({'type':'wait','duration': 5, 'reason':'avoid corridor during time window'})
                    new_steps.append({'type':'navigate_alt','target': s['target'], 'reason':'avoid corridor during time window'})
                    new_steps.append({'type':'inspect_or_adjacent','target': s['target']})
        # 2) If corridor places absent from plan and time window requires, add them explicitly
        corridor_places = [n for n, tags in name_to_tags.items() if 'corridor' in tags]
        if tw:
            for n in corridor_places:
                if n not in [s.get('target') for s in new_steps if 'target' in s]:
                    new_steps.append({'type':'note','text':'08:00-09:00 避免 corridor，必要时等待或改用替代路径'})
                    new_steps.append({'type':'wait','duration': 5, 'reason':'avoid corridor during time window'})
                    new_steps.append({'type':'navigate_alt','target': n, 'reason':'avoid corridor during time window'})
                    new_steps.append({'type':'inspect_or_adjacent','target': n})
        plan['steps'] = new_steps
        # 3) Strengthen rationale if missing or too short
        rat = plan.get('rationale') or ''
        need = ('08:00' in json.dumps(tw) if tw else False)
        if len(rat) < 40 or need:
            pr_str = ','.join(pr_tags) if pr_tags else '无'
            corr_str = ','.join(corridor_places) if corridor_places else '无'
            plan['rationale'] = f"优先处理标签({pr_str})的地点；在时间窗内对走廊({corr_str})绕行并必要时等待；遇设备占用或连续阻塞则拍相邻点并更新记忆；路径选择参考历史动态阻断概率与高成本区域。"
        return plan
