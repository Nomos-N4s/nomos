"""
runner.py — CLI entry point for the Governance Layer reference implementation.

Usage:
    python -m src.governance.runner all
    python -m src.governance.runner all --baselines
    python -m src.governance.runner all --steps 1000 --seeds 20
    python -m src.governance.runner all --baselines --csv results/run.csv
    python -m src.governance.runner gridworld --baselines --strategies governance,monolithic_rl
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from typing import List

from .benchmarks.run_all import (
    run_gridworld_experiments, run_temptation_experiments,
    run_drift_experiments, run_deadlock_experiments,
)
from .benchmarks.report import print_all_reports, format_report
from .experiments.metrics import ExperimentReport

ALL_STRATEGIES = ["governance", "monolithic_rl", "random", "static_masking", "veto_only"]


def _export_csv(reports: List[ExperimentReport], path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "scenario", "strategy", "seed", "step",
                     "reward", "violations", "deadlocks", "runtime_ms"])
        for r in reports:
            ts = datetime.now().isoformat()
            for row in r.metadata.get("step_records", []):
                w.writerow([ts, r.metadata.get("scenario", ""),
                            r.metadata.get("strategy", ""),
                            r.metadata.get("seed", ""),
                            row.get("step", ""),
                            row.get("reward", ""),
                            row.get("violations", ""),
                            row.get("deadlocks", ""),
                            row.get("runtime_ms", "")])


def _build_baseline_flags(args) -> dict:
    flags = {"steps": args.steps, "seeds": args.seeds}
    if getattr(args, "baselines", False):
        strategies = getattr(args, "strategies", None)
        if strategies:
            flags["strategies"] = [s.strip() for s in strategies.split(",")]
        else:
            flags["strategies"] = ALL_STRATEGIES
    return flags


def _run_all_scenarios(flags: dict) -> List[ExperimentReport]:
    all_reports = []
    for runner, scenario in [
        (run_gridworld_experiments, "GridWorld"),
        (run_temptation_experiments, "TemptationBank"),
        (run_drift_experiments, "DriftLab"),
        (run_deadlock_experiments, "DeadlockMaze"),
    ]:
        reports = runner(**flags)
        for r in reports:
            if "scenario" not in r.metadata:
                r.metadata["scenario"] = scenario
        all_reports.extend(reports)
    return all_reports


def cmd_speaker(args):
    from .speaker import _run_speaker_quick_test
    _run_speaker_quick_test()


def cmd_gridworld(args):
    flags = _build_baseline_flags(args)
    reports = run_gridworld_experiments(**flags)
    if args.csv:
        _export_csv(reports, args.csv)
    print_all_reports(reports)


def cmd_temptation(args):
    flags = _build_baseline_flags(args)
    reports = run_temptation_experiments(**flags)
    if args.csv:
        _export_csv(reports, args.csv)
    print_all_reports(reports)


def cmd_drift(args):
    flags = _build_baseline_flags(args)
    reports = run_drift_experiments(**flags)
    if args.csv:
        _export_csv(reports, args.csv)
    print_all_reports(reports)


def cmd_deadlock(args):
    flags = _build_baseline_flags(args)
    reports = run_deadlock_experiments(**flags)
    if args.csv:
        _export_csv(reports, args.csv)
    print_all_reports(reports)


def cmd_all(args):
    t0 = time.time()
    flags = _build_baseline_flags(args)
    reports = _run_all_scenarios(flags)
    elapsed = time.time() - t0

    by_scenario = {}
    for r in reports:
        s = r.metadata.get("scenario", "unknown")
        by_scenario.setdefault(s, []).append(r)

    for scenario, reps in sorted(by_scenario.items()):
        print(f"\n  === {scenario} ===")
        for r in reps:
            strat = r.metadata.get("strategy", "governance")
            seed = r.metadata.get("seed", 0)
            print(f"    [{strat} seed={seed}] {r.name}: steps={r.total_steps} "
                  f"reward={r.total_reward:.1f} "
                  f"deadlocks={r.deadlock_count} "
                  f"violations={r.constraint_violations}")
    print(f"\nTotal time: {elapsed:.2f}s")
    print(f"Total reports: {len(reports)}")

    if args.csv:
        _export_csv(reports, args.csv)
        print(f"CSV exported to {args.csv}")

    if getattr(args, "baselines", False):
        try:
            from .benchmarks.analysis import run_analysis
            from .benchmarks.figures import generate_all_figures
            result = run_analysis(reports, "results")
            print(f"Analysis: {len(result['effect_sizes'])} effect sizes, "
                  f"{len(result['hacking_episodes'])} hacking episodes")
            generate_all_figures(reports, "results/figures")
        except Exception as e:
            print(f"Post-benchmark analysis skipped: {e}")


def cmd_prove(args):
    from .prove.runner import run_all, print_summary, export_json, filter_by_chapter

    results = run_all()

    if args.ch2:
        results = filter_by_chapter(results, "Ch2")
    elif args.ch3:
        results = filter_by_chapter(results, "Ch3")
    elif args.ch4:
        results = filter_by_chapter(results, "Ch4")
    elif args.single:
        results = [r for r in results if r.id == args.single]
        if not results:
            print(f"No prediction found with id={args.single}")
            sys.exit(1)

    print_summary(results)

    if args.json:
        export_json(results, args.json)
        print(f"Exported to {args.json}")


def cmd_adversary(args):
    from .experiments.rl_adversary import main as adversary_main
    sys.argv = ["rl_adversary"] + args.forward_args
    adversary_main()


def _add_shared_args(parser):
    parser.add_argument("--steps", type=int, default=1000,
                        help="Number of steps per run (default: 1000)")
    parser.add_argument("--seeds", type=int, default=1,
                        help="Number of random seeds per strategy-scenario (default: 1)")
    parser.add_argument("--baselines", action="store_true",
                        help="Run all baseline strategies alongside governance")
    parser.add_argument("--strategies", type=str,
                        help="Comma-separated sub-list for selective benchmarking")
    parser.add_argument("--csv", type=str,
                        help="Export results to CSV file")


def main():
    parser = argparse.ArgumentParser(
        description="Governance Layer Reference Implementation"
    )
    sub = parser.add_subparsers(dest="command")

    p_speaker = sub.add_parser("speaker", help="Run quick speaker sanity test")
    p_speaker.set_defaults(func=cmd_speaker)

    for name in ("gridworld", "temptation", "drift", "deadlock"):
        p = sub.add_parser(name, help=f"Run {name} experiment")
        _add_shared_args(p)
        p.set_defaults(func=lambda ns, _n=name: {
            "gridworld": cmd_gridworld,
            "temptation": cmd_temptation,
            "drift": cmd_drift,
            "deadlock": cmd_deadlock,
        }[name](ns))

    p_all = sub.add_parser("all", help="Run all experiments")
    _add_shared_args(p_all)
    p_all.set_defaults(func=cmd_all)

    p_prove = sub.add_parser("prove", help="Verify formal predictions from the book")
    p_prove.add_argument("--all", action="store_true", help="Run all predictions")
    p_prove.add_argument("--ch2", action="store_true", help="Chapter 2 predictions")
    p_prove.add_argument("--ch3", action="store_true", help="Chapter 3 predictions")
    p_prove.add_argument("--ch4", action="store_true", help="Chapter 4 predictions")
    p_prove.add_argument("--single", type=int, metavar="N", help="Single prediction N (1-12)")
    p_prove.add_argument("--json", type=str, help="Export to JSON")
    p_prove.set_defaults(func=cmd_prove)

    p_adv = sub.add_parser("adversary", help="RL adversary experiment (needs torch+sb3)")
    p_adv.add_argument("forward_args", nargs=argparse.REMAINDER)
    p_adv.set_defaults(func=cmd_adversary)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
