import heapq

class Navigator:
    def __init__(self, grid: dict, semantic: dict):
        self.grid = grid
        self.semantic = semantic

    def route(self, start, goal):
        w = self.grid['width']
        H = self.grid['height']
        g = self.grid['grid']
        def in_bounds(x,y):
            return 0 <= x < w and 0 <= y < H
        def passable(x,y):
            if g[y][x] != 0:
                return False
            for ob in self.semantic.get('obstacles', []):
                ox = int(ob.get('x'))
                oy = int(ob.get('y'))
                if ox == x and oy == y:
                    return False
            return True
        def cost(x,y):
            c = 1
            for z in self.semantic.get('high_cost_zones', []):
                if z['xmin'] <= x <= z['xmax'] and z['ymin'] <= y <= z['ymax']:
                    c += z.get('cost',1)
            return c
        def heuristic(a,b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1])
        frontier = []
        heapq.heappush(frontier, (0, start))
        came = {tuple(start): None}
        cost_so_far = {tuple(start): 0}
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx,ny = current[0]+dx, current[1]+dy
                if not in_bounds(nx,ny):
                    continue
                if not passable(nx,ny):
                    continue
                new_cost = cost_so_far[tuple(current)] + cost(nx,ny)
                if (nx,ny) not in cost_so_far or new_cost < cost_so_far[(nx,ny)]:
                    cost_so_far[(nx,ny)] = new_cost
                    priority = new_cost + heuristic((nx,ny), goal)
                    heapq.heappush(frontier, (priority, (nx,ny)))
                    came[(nx,ny)] = current
        path = []
        cur = goal
        if tuple(cur) not in came:
            return []
        while cur is not None:
            path.append(cur)
            cur = came.get(tuple(cur))
        path.reverse()
        return path
