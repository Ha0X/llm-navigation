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
                blocked = None
                if random.random() < 0.1 and len(path) > 3:
                    blocked = path[len(path)//2]
                if blocked:
                    logs.append({'type':'navigate','target':target_name,'result':'blocked','reason':'dynamic','pos':blocked})
                    self.memory.append_episodic({'place':target_name,'action':'navigate','result':'blocked','cost':0,'reason':'dynamic'})
                    path1 = [p for p in path if p != blocked]
                    pos = path1[-1] if path1 else pos
                    path2 = self.navigator.route(pos, tgt)
                    for p in path2:
                        trajectory.append(p)
                    pos = path2[-1] if path2 else pos
                else:
                    for p in path:
                        trajectory.append(p)
                    pos = path[-1]
                    logs.append({'type':'navigate','target':target_name,'result':'ok','pos':pos})
                    self.memory.append_episodic({'place':target_name,'action':'navigate','result':'ok','cost':len(path),'reason':'none'})
            elif step['type'] == 'inspect':
                logs.append({'type':'inspect','target':step['target'],'result':'ok'})
                self.memory.append_episodic({'place':step['target'],'action':'inspect','result':'ok','cost':1,'reason':'none'})
        delta = self.memory.reflect(logs)
        return trajectory, logs

    def _loc_xy(self, locations, name):
        for p in locations.get('places', []):
            if p.get('name') == name:
                return (int(p['x']), int(p['y']))
        return None
