import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from agent.core.memory import MemoryStore
from agent.core.planner import Planner
from agent.core.navigator import Navigator
from agent.core.executor import Executor
from agent.core.reporter import Reporter
from agent.core.llm import configure as llm_configure
from time import perf_counter
from agent.core.charts import metrics_to_svg

def load_grid(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_locations(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_config(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def cmd_show_plan(args):
    root = Path('.')
    grid = load_grid(root / 'maps' / 'grid.json')
    locations = load_locations(root / 'maps' / 'locations.json')
    config = load_config(root / 'config.json')
    if getattr(args, 'api_key', None) and getattr(args, 'base_url', None):
        llm_configure(args.api_key, args.base_url)
    memory = MemoryStore(root / 'memory')
    memory_ctx = memory.retrieve(args.task, locations, k=5)
    planner = Planner()
    try:
        plan = planner.plan(args.task, memory_ctx, locations, config)
    except Exception as e:
        console = Console()
        console.print(f"[red]Planner error:[/red] {e}")
        console.print("[yellow]Hint:[/yellow] provide --api_key and --base_url to enable LLM planning")
        return
    out_dir = root / 'out'
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / 'plan.json').open('w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    table = Table(title="Plan")
    table.add_column("Step")
    table.add_column("Target")
    for s in plan.get('steps', []):
        table.add_row(s.get('type',''), s.get('target',''))
    console = Console()
    console.print(table)
    console.print('Plan saved at ' + str(out_dir / 'plan.json'))

def cmd_run(args):
    root = Path('.')
    grid = load_grid(root / 'maps' / 'grid.json')
    locations = load_locations(root / 'maps' / 'locations.json')
    config = load_config(root / 'config.json')
    if getattr(args, 'api_key', None) and getattr(args, 'base_url', None):
        llm_configure(args.api_key, args.base_url)
    memory = MemoryStore(root / 'memory')
    memory_ctx = memory.retrieve(args.task, locations, k=5)
    planner = Planner()
    try:
        plan = planner.plan(args.task, memory_ctx, locations, config)
    except Exception as e:
        console = Console()
        console.print(f"[red]Planner error:[/red] {e}")
        console.print("[yellow]Hint:[/yellow] provide --api_key and --base_url to enable LLM planning")
        return
    navigator = Navigator(grid, memory.semantic)
    executor = Executor(navigator, memory)
    trajectory, logs = executor.run(plan, locations, config)
    reporter = Reporter()
    out_dir = Path('out')
    out_dir.mkdir(parents=True, exist_ok=True)
    reporter.export(plan, trajectory, logs, memory_ctx, out_dir)
    console = Console()
    console.print('[green]Report generated[/green] at ' + str(out_dir / 'report.md'))

def cmd_clean(args):
    root = Path('.')
    out_dir = root / 'out'
    if out_dir.exists():
        for p in out_dir.iterdir():
            try:
                p.unlink()
            except IsADirectoryError:
                pass
    ep = root / 'memory' / 'episodic.jsonl'
    if ep.exists():
        ep.write_text('', encoding='utf-8')
    console = Console()
    console.print('[green]Cleaned[/green] outputs and episodic memory')

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p1 = sub.add_parser('show_plan')
    p1.add_argument('task', type=str)
    p1.add_argument('--api_key', type=str, default=None)
    p1.add_argument('--base_url', type=str, default=None)
    p1.set_defaults(func=cmd_show_plan)
    p2 = sub.add_parser('run')
    p2.add_argument('task', type=str)
    p2.add_argument('--api_key', type=str, default=None)
    p2.add_argument('--base_url', type=str, default=None)
    p2.set_defaults(func=cmd_run)
    p3 = sub.add_parser('eval')
    p3.add_argument('tasks_file', type=str)
    p3.add_argument('--api_key', type=str, default=None)
    p3.add_argument('--base_url', type=str, default=None)
    p3.add_argument('--baseline', type=str, choices=['random','greedy'], default='greedy')
    p3.set_defaults(func=cmd_eval)
    p4 = sub.add_parser('clean')
    p4.set_defaults(func=cmd_clean)
    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        return
    args.func(args)
def _run_once(task: str, use_memory: bool, api_key: str, base_url: str, baseline: str = 'greedy'):
    root = Path('.')
    grid = load_grid(root / 'maps' / 'grid.json')
    locations = load_locations(root / 'maps' / 'locations.json')
    config = load_config(root / 'config.json')
    if api_key and base_url:
        llm_configure(api_key, base_url)
    memory = MemoryStore(root / 'memory')
    memory_ctx = memory.retrieve(task, locations, k=5) if use_memory else {'episodes':[], 'semantic': memory.semantic, 'procedural': memory.procedural}
    planner = Planner()
    t0 = perf_counter()
    try:
        plan = planner.plan(task, memory_ctx, locations, config)
    except Exception:
        if baseline == 'random':
            from agent.core.baselines import plan_random
            plan = plan_random(task, locations)
        else:
            from agent.core.baselines import plan_greedy_distance
            plan = plan_greedy_distance(task, locations, config.get('start', {'x':0,'y':0}))
    navigator = Navigator(grid, memory.semantic if use_memory else {'high_cost_zones': []})
    executor = Executor(navigator, memory if use_memory else memory)
    trajectory, logs = executor.run(plan, locations, config)
    t1 = perf_counter()
    length = len(trajectory)
    blocked = sum(1 for l in logs if l.get('result') == 'blocked')
    return {'task': task, 'use_memory': use_memory, 'time_sec': round(t1 - t0, 4), 'path_len': length, 'blocked': blocked}

def cmd_eval(args):
    tasks_path = Path(args.tasks_file)
    tasks = []
    with tasks_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(line)
    results = []
    for t in tasks:
        r0 = _run_once(t, use_memory=False, api_key=args.api_key, base_url=args.base_url, baseline=args.baseline)
        r1 = _run_once(t, use_memory=True, api_key=args.api_key, base_url=args.base_url, baseline=args.baseline)
        results.extend([r0, r1])
    out_dir = Path('out')
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_csv = out_dir / 'metrics.csv'
    with metrics_csv.open('w', encoding='utf-8') as f:
        f.write('task,use_memory,time_sec,path_len,blocked\n')
        for r in results:
            f.write(f"{r['task']},{int(r['use_memory'])},{r['time_sec']},{r['path_len']},{r['blocked']}\n")
    svg_path = out_dir / 'metrics.svg'
    metrics_to_svg(str(metrics_csv), str(svg_path))
    print('Metrics saved at', str(metrics_csv))
    print('Chart saved at', str(svg_path))

if __name__ == '__main__':
    main()
