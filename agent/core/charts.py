import csv

def metrics_to_svg(csv_path: str, svg_path: str):
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    tasks = sorted(list({r['task'] for r in rows}))
    w = 800
    h = 300
    pad = 40
    bar_w = max(10, int((w - 2*pad) / (len(tasks)*3)))
    def scale(values):
        m = max(values) if values else 1
        return lambda v: int((h - 2*pad) * (v / m))
    times_baseline = [float(next(r['time_sec'] for r in rows if r['task']==t and r['use_memory']=='0')) for t in tasks]
    times_memory = [float(next(r['time_sec'] for r in rows if r['task']==t and r['use_memory']=='1')) for t in tasks]
    scl_time = scale(times_baseline + times_memory)
    x = pad
    bars = []
    for i, t in enumerate(tasks):
        tb = float(next(r['time_sec'] for r in rows if r['task']==t and r['use_memory']=='0'))
        tm = float(next(r['time_sec'] for r in rows if r['task']==t and r['use_memory']=='1'))
        hb = scl_time(tb)
        hm = scl_time(tm)
        xb = pad + i*3*bar_w
        xm = xb + bar_w
        bars.append((xb, h-pad-hb, bar_w, hb, '#888', f'{t} baseline {tb}s'))
        bars.append((xm, h-pad-hm, bar_w, hm, '#4caf50', f'{t} memory {tm}s'))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">']
    svg.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fff"/>')
    svg.append(f'<text x="{pad}" y="{pad-10}" font-size="14">Time: memory vs baseline</text>')
    for (x,y,bw,bh,color,label) in bars:
        svg.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{color}"/>')
    svg.append('</svg>')
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
