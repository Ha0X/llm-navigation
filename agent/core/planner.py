import re
import json
from typing import List, Dict, Any
from agent.core.llm import json_response

class Planner:
    def plan(self, task_text: str, memory_ctx: Dict[str, Any], locations: Dict[str, Any], config: Dict[str, Any]):
        llm_out = json_response(
            system="你是一个机器人任务规划器。严格返回JSON，不要解释。遵守约束：避开高代价区域与障碍，考虑地点标签与优先级，必要时加入等待或备注步骤。",
            user=json.dumps({
                "task": task_text,
                "locations": [p['name'] for p in locations.get('places', [])],
                "location_tags": {p['name']: p.get('tags', []) for p in locations.get('places', [])},
                "memory_tips": memory_ctx.get('procedural', {}).get('skills', {}).get('navigate', {}).get('tips', []),
                "semantic": memory_ctx.get('semantic', {}),
                "deadline": self._extract_constraints(task_text)
            }, ensure_ascii=False),
            schema_hint='返回形如{"order":["A","B"],"steps":[{"type":"navigate","target":"A"},{"type":"inspect","target":"A"},{"type":"wait","duration":10},{"type":"note","text":"避开走廊"}],"milestones":[{"name":"到达A","eta_min":5}],"notes":[]}'
        )
        if not llm_out or not isinstance(llm_out, dict):
            raise ValueError('LLM planning failed')
        order = llm_out.get('order')
        steps = llm_out.get('steps')
        if not steps:
            raise ValueError('LLM planning returned empty steps')
        plan = {'task': task_text, 'steps': steps, 'constraints': self._extract_constraints(task_text)}
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
        return {'deadline_minutes': deadline}

    def _apply_priority(self, task_text: str, order: List[str]) -> List[str]:
        m = re.search(r'优先([A-Z])', task_text)
        if not m or not order:
            return order
        p = m.group(1)
        if p in order:
            new = [p] + [x for x in order if x != p]
            return new
        return order
