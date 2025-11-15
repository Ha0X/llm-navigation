import json
from pathlib import Path
from .visual import draw_map_and_trajectory
from .visual import draw_animated_sim

class Reporter:
    def export(self, plan: dict, trajectory: list, logs: list, memory_ctx: dict, out_dir: Path):
        with (out_dir / 'plan.json').open('w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        with (out_dir / 'trajectory.json').open('w', encoding='utf-8') as f:
            json.dump({'trajectory': trajectory}, f, ensure_ascii=False, indent=2)
        with (out_dir / 'logs.json').open('w', encoding='utf-8') as f:
            json.dump({'logs': logs}, f, ensure_ascii=False, indent=2)
        try:
            draw_map_and_trajectory(Path('maps/grid.json'), Path('maps/locations.json'), trajectory, memory_ctx.get('semantic', {}), out_dir / 'map_trajectory.svg', logs)
        except Exception:
            pass
        try:
            draw_animated_sim(Path('maps/grid.json'), Path('maps/locations.json'), trajectory, memory_ctx.get('semantic', {}), out_dir / 'anim.svg')
        except Exception:
            pass
        report = []
        report.append('# Agent Report')
        report.append('## Task')
        report.append(plan.get('task',''))
        report.append('## Steps')
        for s in plan.get('steps', []):
            report.append(f"- {s['type']} -> {s['target']}")
        report.append('## Logs')
        for l in logs:
            t = l.get('type')
            r = l.get('result')
            target = l.get('target')
            report.append(f"- {t} {target} {r}")
        report.append('## Memory References')
        eps = memory_ctx.get('episodes', [])
        for e in eps:
            report.append(f"- {e.get('action')} {e.get('place')} {e.get('result')}")
        (out_dir / 'report.md').write_text("\n".join(report), encoding='utf-8')
