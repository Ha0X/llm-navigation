import json
from pathlib import Path

def draw_map_and_trajectory(grid_path: Path, locations_path: Path, trajectory: list, semantic: dict, out_svg: Path, logs: list = None):
    with grid_path.open('r', encoding='utf-8') as f:
        grid = json.load(f)
    with locations_path.open('r', encoding='utf-8') as f:
        locs = json.load(f)
    w = grid['width']
    h = grid['height']
    cell = 20
    W = w*cell
    H = h*cell
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">']
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    g = grid['grid']
    for y in range(h):
        for x in range(w):
            if g[y][x] != 0:
                svg.append(f'<rect x="{x*cell}" y="{y*cell}" width="{cell}" height="{cell}" fill="#333"/>')
    for z in semantic.get('high_cost_zones', []):
        x = z['xmin']*cell
        y = z['ymin']*cell
        ww = (z['xmax']-z['xmin']+1)*cell
        hh = (z['ymax']-z['ymin']+1)*cell
        svg.append(f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="#ffcc00" opacity="0.3"/>')
    for ob in semantic.get('obstacles', []):
        ox = int(ob.get('x'))*cell
        oy = int(ob.get('y'))*cell
        svg.append(f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="#c00"/>')
    visits = {}
    for (x,y) in trajectory or []:
        visits[(x,y)] = visits.get((x,y), 0) + 1
    if visits:
        m = max(visits.values())
        for (x,y), c in visits.items():
            op = 0.2 + 0.6 * (c / m)
            svg.append(f'<rect x="{x*cell}" y="{y*cell}" width="{cell}" height="{cell}" fill="#4caf50" opacity="{op}"/>')
    for p in locs.get('places', []):
        px = int(p['x'])*cell
        py = int(p['y'])*cell
        svg.append(f'<circle cx="{px+cell/2}" cy="{py+cell/2}" r="{cell/3}" fill="#1e88e5"/>')
        svg.append(f'<text x="{px+cell/2}" y="{py+cell/2}" font-size="10" text-anchor="middle" dominant-baseline="middle" fill="#000">{p["name"]}</text>')
    if trajectory:
        pts = ' '.join([f'{x*cell+cell/2},{y*cell+cell/2}' for (x,y) in trajectory])
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#2e7d32" stroke-width="2"/>')
    if logs:
        for l in logs:
            if l.get('result') == 'blocked' and l.get('pos'):
                bx = int(l['pos'][0]) * cell + cell/2
                by = int(l['pos'][1]) * cell + cell/2
                d = cell/2
                svg.append(f'<line x1="{bx-d}" y1="{by-d}" x2="{bx+d}" y2="{by+d}" stroke="#d32f2f" stroke-width="2"/>')
                svg.append(f'<line x1="{bx-d}" y1="{by+d}" x2="{bx+d}" y2="{by-d}" stroke="#d32f2f" stroke-width="2"/>')
    svg.append('</svg>')
    out_svg.write_text('\n'.join(svg), encoding='utf-8')

def draw_animated_sim(grid_path: Path, locations_path: Path, trajectory: list, semantic: dict, out_svg: Path):
    with grid_path.open('r', encoding='utf-8') as f:
        grid = json.load(f)
    with locations_path.open('r', encoding='utf-8') as f:
        locs = json.load(f)
    w = grid['width']
    h = grid['height']
    cell = 20
    W = w*cell
    H = h*cell
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">']
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    g = grid['grid']
    for y in range(h):
        for x in range(w):
            if g[y][x] != 0:
                svg.append(f'<rect x="{x*cell}" y="{y*cell}" width="{cell}" height="{cell}" fill="#333"/>')
    for z in semantic.get('high_cost_zones', []):
        x = z['xmin']*cell
        y = z['ymin']*cell
        ww = (z['xmax']-z['xmin']+1)*cell
        hh = (z['ymax']-z['ymin']+1)*cell
        svg.append(f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="#ffcc00" opacity="0.3"/>')
    path_cmds = []
    for i, (x,y) in enumerate(trajectory or []):
        px = x*cell + cell/2
        py = y*cell + cell/2
        if i == 0:
            path_cmds.append(f'M {px} {py}')
        else:
            path_cmds.append(f'L {px} {py}')
    path_str = ' '.join(path_cmds)
    svg.append(f'<path d="{path_str}" fill="none" stroke="#2e7d32" stroke-width="2"/>')
    dur = max(2, int((len(trajectory or []) + 1) / 4))
    svg.append('<g>')
    svg.append(f'<circle r="6" fill="#1e88e5">')
    svg.append(f'<animateMotion begin="0s" dur="{dur}s" fill="freeze" repeatCount="1" path="{path_str}"/>')
    svg.append('</circle>')
    svg.append('</g>')
    svg.append('</svg>')
    out_svg.write_text('\n'.join(svg), encoding='utf-8')
