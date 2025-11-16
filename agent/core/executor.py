import random

class Executor:
    def __init__(self, navigator, memory_store):
        self.navigator = navigator
        self.memory = memory_store

    def run(self, plan: dict, locations: dict, config: dict):
        start = config.get('start', {'x':0,'y':0})
        pos = (int(start['x']), int(start['y']))
        logs = []
        trajectory = [pos]
        for step in plan.get('steps', []):
            if step['type'] == 'navigate':
                target_name = step['target']
                tgt = self._loc_xy(locations, target_name)
                if not tgt:
                    logs.append({'type':'navigate','target':target_name,'result':'fail','reason':'unknown_target','pos':pos})
                    continue
                path = self.navigator.route(pos, tgt)
                if not path:
                    logs.append({'type':'navigate','target':target_name,'result':'fail','reason':'no_path','pos':pos})
                    self.memory.append_episodic({'place':target_name,'action':'navigate','result':'fail','cost':0,'reason':'no_path'})
                    continue
                i = 0
                blocked_count = 0
                while i < len(path):
                    p = path[i]
                    trajectory.append(p)
                    pos = p
                    if random.random() < 0.05:
                        logs.append({'type':'navigate','target':target_name,'result':'blocked','reason':'dynamic','pos':pos})
                        self.memory.append_episodic({'place':target_name,'action':'navigate','result':'blocked','cost':0,'reason':'dynamic'})
                        blocked_count += 1
                        if blocked_count >= 2:
                            adj = self._adjacent_point(locations, target_name)
                            if adj:
                                logs.append({'type':'fallback','target':target_name,'action':'inspect_adjacent','adjacent':adj,'result':'ok'})
                                self.memory.append_episodic({'place':target_name,'action':'inspect_adjacent','result':'ok','cost':1,'reason':'busy'})
                                break
                        new_path = self.navigator.route(pos, tgt)
                        path = new_path
                        i = 0
                        continue
                    i += 1
                logs.append({'type':'navigate','target':target_name,'result':'ok','pos':pos})
                self.memory.append_episodic({'place':target_name,'action':'navigate','result':'ok','cost':len(path),'reason':'none'})
            elif step['type'] == 'navigate_alt':
                target_name = step['target']
                logs.append({'type':'navigate_alt','target':target_name,'reason': step.get('reason','')})
                tgt = self._loc_xy(locations, target_name)
                path = self.navigator.route(pos, tgt)
                for p in path:
                    trajectory.append(p)
                    pos = p
                logs.append({'type':'navigate_alt','target':target_name,'result':'ok','pos':pos})
            elif step['type'] == 'inspect_or_adjacent':
                target_name = step['target']
                busy = random.random() < 0.2
                if busy:
                    adj = self._adjacent_point(locations, target_name)
                    if adj:
                        logs.append({'type':'inspect_adjacent','target':target_name,'adjacent':adj,'result':'ok'})
                        self.memory.append_episodic({'place':target_name,'action':'inspect_adjacent','result':'ok','cost':1,'reason':'busy'})
                        continue
                logs.append({'type':'inspect','target':target_name,'result':'ok'})
                self.memory.append_episodic({'place':target_name,'action':'inspect','result':'ok','cost':1,'reason':'none'})
            elif step['type'] == 'inspect':
                logs.append({'type':'inspect','target':step['target'],'result':'ok'})
                self.memory.append_episodic({'place':step['target'],'action':'inspect','result':'ok','cost':1,'reason':'none'})
            elif step['type'] == 'wait':
                logs.append({'type':'wait','duration': step.get('duration', 0), 'result':'ok', 'reason': step.get('reason','')})
            elif step['type'] == 'note':
                logs.append({'type':'note','text': step.get('text','')})
        delta = self.memory.reflect(logs)
        return trajectory, logs

    def _loc_xy(self, locations, name):
        for p in locations.get('places', []):
            if p.get('name') == name:
                return (int(p['x']), int(p['y']))
        return None

    def _adjacent_point(self, locations, name):
        for p in locations.get('places', []):
            if p.get('name') == name:
                x,y = int(p['x']), int(p['y'])
                return (x+1, y)
        return None
