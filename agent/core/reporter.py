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
        if plan.get('rationale'):
            report.append('## Rationale')
            report.append(plan.get('rationale',''))
        if plan.get('errors'):
            report.append('## Errors')
            for e in plan.get('errors', []):
                report.append(f"- {e}")
        report.append('## Steps')
        for s in plan.get('steps', []):
            t = s.get('type','')
            tgt = s.get('target','')
            if t:
                if tgt:
                    report.append(f"- {t} -> {tgt}")
                else:
                    report.append(f"- {t}")
        report.append('## Logs')
        for l in logs:
            t = l.get('type')
            r = l.get('result')
            target = l.get('target')
            if t in ('navigate','navigate_alt'):
                reason = l.get('reason','')
                pos = l.get('pos','')
                report.append(f"- {t} {target} {r} {reason} {pos}")
            elif t == 'fallback':
                adj = l.get('adjacent','')
                report.append(f"- fallback {target} -> inspect_adjacent {adj} {r}")
            else:
                report.append(f"- {t} {target} {r}")
        report.append('## Memory References')
        dyn = memory_ctx.get('semantic', {}).get('dynamic_blocks', [])
        for o in dyn[:5]:
            report.append(f"- dynamic_block ({o.get('x')},{o.get('y')}) conf={o.get('confidence')}")
        for z in memory_ctx.get('semantic', {}).get('high_cost_zones', []):
            report.append(f"- high_cost_zone x=[{z['xmin']},{z['xmax']}] y=[{z['ymin']},{z['ymax']}] cost={z.get('cost',1)}")
        (out_dir / 'report.md').write_text("\n".join(report), encoding='utf-8')
