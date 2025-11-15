import re
import math

def _extract_order(task_text: str, location_names):
    arrow = re.split(r"\s*(?:→|->|-)\s*", task_text)
    names = [s.strip() for s in arrow if re.fullmatch(r"[A-Z]", s.strip())]
    tokens = re.findall(r"([A-Z])", task_text)
    ordered = []
    seen = set()
    for s in names + tokens:
        if s in location_names and s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered

def plan_random(task_text: str, locations: dict):
    names = [p['name'] for p in locations.get('places', [])]
    import random
    random.shuffle(names)
    steps = []
    for n in names:
        steps.append({'type':'navigate','target':n})
        steps.append({'type':'inspect','target':n})
    return {'task': task_text, 'steps': steps, 'constraints': {}}

def plan_greedy_distance(task_text: str, locations: dict, start: dict):
    loc_map = {p['name']:(int(p['x']), int(p['y'])) for p in locations.get('places', [])}
    order_hint = _extract_order(task_text, list(loc_map.keys()))
    remaining = list(loc_map.keys())
    if order_hint:
        remaining = [n for n in remaining if n in order_hint] + [n for n in remaining if n not in order_hint]
    cur = (int(start.get('x',0)), int(start.get('y',0)))
    ordered = []
    rem = set(remaining)
    while rem:
        best = None
        best_d = None
        for n in list(rem):
            xy = loc_map[n]
            d = abs(cur[0]-xy[0]) + abs(cur[1]-xy[1])
            if best is None or d < best_d:
                best = n
                best_d = d
        ordered.append(best)
        cur = loc_map[best]
        rem.remove(best)
    steps = []
    for n in ordered:
        steps.append({'type':'navigate','target':n})
        steps.append({'type':'inspect','target':n})
    return {'task': task_text, 'steps': steps, 'constraints': {}}
