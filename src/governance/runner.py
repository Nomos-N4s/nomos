"""
CLI entry point for the Governance Layer reference implementation.

Provides commands for running experiments, verifying formal predictions,
and exporting results.

Usage:
    ``python -m src.governance.runner all``
    ``python -m src.governance.runner all --baselines --steps 1000 --seeds 20``
    ``python -m src.governance.runner all --baselines --csv results/run.csv``
    ``python -m src.governance.runner gridworld --baselines --strategies governance,monolithic_rl``
    ``python -m src.governance.runner gridworld --config examples/grid_world.parliament``
    ``python -m src.governance.runner prove --all``
    ``python -m src.governance.runner prove --ch4``
    ``python -m src.governance.runner agent --seeds 20 --model openrouter:nvidia/nemotron-3-ultra-550b-a55b:free``
    ``python -m src.governance.runner agent --seeds 1 --steps 30 --stub``
"""

import argparse
import csv
import importlib
import json
import os
import sys
import time
from datetime import datetime

from .agents.cache import DEFAULT_CACHE_DIR
from .benchmarks.report import print_all_reports
from .benchmarks.run_all import (
    run_deadlock_experiments,
    run_drift_experiments,
    run_gridworld_experiments,
    run_temptation_experiments,
)
from .committee.base import ParliamentMember
from .contracts.contract import UlyssesContract
from .dsl import ParliamentConfig, parse_file, validate
from .experiments.metrics import ExperimentReport
from .speaker import SpeakerStateMachine

ALL_STRATEGIES = ["governance", "monolithic_rl", "random", "static_masking", "veto_only"]


def build_from_config(config_path: str) -> SpeakerStateMachine:
    """Parse a .parliament file and build a fully-configured Speaker.

    Args:
        config_path: Path to a .parliament configuration file.

    Returns:
        A :class:`~.speaker.SpeakerStateMachine` with members, contracts,
        and parameters configured from the file.

    Usage:
        ``python -m src.governance.runner gridworld --config examples/grid_world.parliament``
    """
    config = parse_file(config_path)
    validate(config)

    members = _build_members(config)
    speaker = SpeakerStateMachine(
        members=members,
        default_action=config.speaker.default_action,
        majority_threshold=config.speaker.majority_threshold,
        supermajority_threshold=config.speaker.supermajority_threshold,
        max_rounds=config.speaker.max_rounds,
    )
    return speaker


def _build_members(config: ParliamentConfig) -> dict[str, ParliamentMember]:
    members: dict[str, ParliamentMember] = {}
    for mc in config.members:
        cls = _import_member_class(mc.class_name)
        member = cls()
        member.member_id = mc.member_id
        member.veto_threshold = mc.veto_threshold
        member.weight = mc.weight
        member.budget = mc.budget
        members[member.member_id] = member
    return members


def _import_member_class(class_name: str) -> type[ParliamentMember]:
    mod = importlib.import_module("governance.committee.members")
    if hasattr(mod, class_name):
        return getattr(mod, class_name)
    example_name = f"Example{class_name}"
    if hasattr(mod, example_name):
        return getattr(mod, example_name)
    if "." in class_name:
        parts = class_name.split(".")
        mod = importlib.import_module(".".join(parts[:-1]))
        return getattr(mod, parts[-1])
    msg = f"cannot import ParliamentMember class '{class_name}'"
    raise ImportError(msg)


def _build_contracts(config: ParliamentConfig) -> list[UlyssesContract]:
    contracts: list[UlyssesContract] = []
    for cc in config.contracts:
        contracts.append(
            UlyssesContract(
                contract_id=cc.contract_id,
                restricted_indices=set(cc.restricted_indices),
                enactment_threshold=cc.enactment_threshold,
                revocation_threshold=cc.revocation_threshold,
                enforcement_mode=cc.enforcement_mode,
            )
        )
    return contracts


def _resolve_csv_path(csv_arg: str | None) -> str | None:
    if csv_arg is None:
        return None
    if csv_arg == "":
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"results/run_{ts}.csv"
    return csv_arg


def _export_csv(reports: list[ExperimentReport], path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "timestamp",
                "scenario",
                "strategy",
                "seed",
                "step",
                "reward",
                "violations",
                "deadlocks",
                "runtime_ms",
            ]
        )
        for r in reports:
            ts = datetime.now().isoformat()
            for row in r.metadata.get("step_records", []):
                w.writerow(
                    [
                        ts,
                        r.metadata.get("scenario", ""),
                        r.metadata.get("strategy", ""),
                        r.metadata.get("seed", ""),
                        row.get("step", ""),
                        row.get("reward", ""),
                        row.get("violations", ""),
                        row.get("deadlocks", ""),
                        row.get("runtime_ms", ""),
                    ]
                )


def _build_baseline_flags(args) -> dict:
    flags = {"steps": args.steps, "seeds": args.seeds}
    if getattr(args, "baselines", False):
        strategies = getattr(args, "strategies", None)
        if strategies:
            flags["strategies"] = [s.strip() for s in strategies.split(",")]
        else:
            flags["strategies"] = ALL_STRATEGIES
    config_path = getattr(args, "config", None)
    if config_path:
        flags["config_path"] = config_path
    return flags


def _run_all_scenarios(flags: dict) -> list[ExperimentReport]:
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


def _optionally_export_csv(args, reports):
    csv_path = _resolve_csv_path(getattr(args, "csv", None))
    if csv_path:
        _export_csv(reports, csv_path)
        print(f"CSV exported to {csv_path}")


def cmd_gridworld(args):
    flags = _build_baseline_flags(args)
    reports = run_gridworld_experiments(**flags)
    _optionally_export_csv(args, reports)
    print_all_reports(reports)


def cmd_temptation(args):
    flags = _build_baseline_flags(args)
    reports = run_temptation_experiments(**flags)
    _optionally_export_csv(args, reports)
    print_all_reports(reports)


def cmd_drift(args):
    flags = _build_baseline_flags(args)
    reports = run_drift_experiments(**flags)
    _optionally_export_csv(args, reports)
    print_all_reports(reports)


def cmd_deadlock(args):
    flags = _build_baseline_flags(args)
    reports = run_deadlock_experiments(**flags)
    _optionally_export_csv(args, reports)
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
            print(
                f"    [{strat} seed={seed}] {r.name}: steps={r.total_steps} "
                f"reward={r.total_reward:.1f} "
                f"deadlocks={r.deadlock_count} "
                f"violations={r.constraint_violations}"
            )
    print(f"\nTotal time: {elapsed:.2f}s")
    print(f"Total reports: {len(reports)}")

    _optionally_export_csv(args, reports)

    if getattr(args, "baselines", False):
        try:
            from .benchmarks.analysis import run_analysis
            from .benchmarks.figures import generate_all_figures

            result = run_analysis(reports, "results")
            print(
                f"Analysis: {len(result['effect_sizes'])} effect sizes, "
                f"{len(result['hacking_episodes'])} hacking episodes"
            )
            generate_all_figures(reports, "results/figures")
        except Exception as e:
            print(f"Post-benchmark analysis skipped: {e}")


def cmd_prove(args):
    from .prove.runner import export_json, filter_by_chapter, print_summary, run_all

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

    csv_path = _resolve_csv_path(getattr(args, "csv", None))
    if csv_path:
        import csv as _csv

        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        with open(csv_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["id", "chapter", "prediction", "status", "details"])
            for r in results:
                w.writerow([r.id, r.chapter, r.name, r.status, r.details])
        print(f"CSV exported to {csv_path}")


def cmd_prove_agent(args):
    from .agents import DEFAULT_CACHE_DIR, run_cross_validation
    from .agents.prediction_harness import CrossValidationResult

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    temperatures = [float(t.strip()) for t in args.temperatures.split(",") if t.strip()]
    prediction_ids = None
    if getattr(args, "predictions", None):
        prediction_ids = [int(p.strip()) for p in args.predictions.split(",") if p.strip()]

    cache_dir = args.cache if args.cache else DEFAULT_CACHE_DIR
    backend_factory = None
    if args.stub:

        def _stub_factory(scenario):
            return None

        backend_factory = _stub_factory

    result: CrossValidationResult = run_cross_validation(
        seeds=args.seeds,
        steps=args.steps,
        backend_factory=backend_factory,
        models=models,
        temperatures=temperatures,
        prediction_ids=prediction_ids,
        use_cache=not args.no_cache,
        cache_dir=cache_dir,
    )

    print(result.to_markdown())

    output_dir = "results/agent"
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, "prediction_cross_validation.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result.to_markdown())
    json_path = os.path.join(output_dir, "prediction_cross_validation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.to_json(), f, indent=2)
    print(f"\nReports written to {output_dir}/")
    print(f"  {md_path}")
    print(f"  {json_path}")


def cmd_adversary(args):
    from .experiments.rl_adversary import main as adversary_main

    sys.argv = ["rl_adversary"] + args.forward_args
    adversary_main()


def _build_pydanticai_factory(model: str | None, temperature: float | None):
    """Backend factory for real LLM runs (one adapter per scenario).

    Each scenario briefs the agent with its own system prompt, so a
    fresh adapter is built per scenario inside the factory.

    Args:
        model: Provider-prefixed model string (may be None to use the
            ``GOVERNANCE_LLM_MODEL`` env var or the adapter default).
        temperature: Sampling temperature.

    Returns:
        A ``(scenario) -> PydanticAIAdapter`` factory.
    """
    from .agents.pydantic_adapter import PydanticAIAdapter

    def factory(scenario):
        return PydanticAIAdapter(
            system_prompt=scenario.system_prompt(),
            model=model,
            temperature=temperature,
        )

    return factory


def cmd_agent(args):
    from .agents import DEFAULT_CACHE_DIR
    from .agents.pipeline import run_agent_benchmark
    from .agents.report import format_agent_summary

    cache_dir = args.cache if args.cache else DEFAULT_CACHE_DIR
    backend_factory = None
    if args.backend == "pydanticai":
        backend_factory = _build_pydanticai_factory(args.model, args.temperature)

    result = run_agent_benchmark(
        seeds=args.seeds,
        steps=args.steps,
        backend_factory=backend_factory,
        use_cache=not args.no_cache,
        cache_dir=cache_dir,
    )

    summary = result["analysis"]["summary"]
    print(format_agent_summary(summary))
    print(f"Cache: {result['cache_stats']} entries in {cache_dir}")
    print(f"Cache manifest: {result['manifest_path']}")
    print(
        "Reports written to results/agent/ "
        "(report.md, benchmark_results.json, benchmark_summary.csv)"
    )


def _add_shared_args(parser):
    parser.add_argument(
        "--steps", type=int, default=1000, help="Number of steps per run (default: 1000)"
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="Number of random seeds per strategy-scenario (default: 1)",
    )
    parser.add_argument(
        "--baselines", action="store_true", help="Run all baseline strategies alongside governance"
    )
    parser.add_argument(
        "--strategies", type=str, help="Comma-separated sub-list for selective benchmarking"
    )
    parser.add_argument(
        "--csv",
        nargs="?",
        const="",
        default=None,
        help="Export results to CSV (default: results/run_<timestamp>.csv)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to .parliament config file (replaces hardcoded Speaker setup)",
    )

    def _validate_positive(parser, ns):
        if ns.steps is not None and ns.steps < 1:
            parser.error("--steps must be > 0")
        if ns.seeds is not None and ns.seeds < 1:
            parser.error("--seeds must be > 0")

    parser.set_defaults(_validate=_validate_positive)


def main():
    parser = argparse.ArgumentParser(description="Governance Layer Reference Implementation")
    sub = parser.add_subparsers(dest="command")

    p_speaker = sub.add_parser("speaker", help="Run quick speaker sanity test")
    p_speaker.set_defaults(func=cmd_speaker)

    for name in ("gridworld", "temptation", "drift", "deadlock"):
        p = sub.add_parser(name, help=f"Run {name} experiment")
        _add_shared_args(p)
        p.set_defaults(
            func=lambda ns, _n=name: {
                "gridworld": cmd_gridworld,
                "temptation": cmd_temptation,
                "drift": cmd_drift,
                "deadlock": cmd_deadlock,
            }[_n](ns)
        )

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
    p_prove.add_argument(
        "--csv",
        nargs="?",
        const="",
        default=None,
        help="Export to CSV (default: results/run_<timestamp>.csv)",
    )
    p_prove.set_defaults(func=cmd_prove)

    p_prove_agent = sub.add_parser(
        "prove-agent",
        help="Cross-validate formal predictions against LLM agent benchmark runs",
    )
    p_prove_agent.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="Number of random seeds per prediction-scenario-model-temp (default: 1)",
    )
    p_prove_agent.add_argument(
        "--steps",
        type=int,
        default=50,
        help="Steps per arm per seed (default: 50)",
    )
    p_prove_agent.add_argument(
        "--models",
        type=str,
        default="openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
        help="Comma-separated model strings (default: reference model from REPRODUCIBILITY.md)",
    )
    p_prove_agent.add_argument(
        "--temperatures",
        type=str,
        default="0.0",
        help="Comma-separated sampling temperatures (default: 0.0)",
    )
    p_prove_agent.add_argument(
        "--predictions",
        type=str,
        default=None,
        help="Comma-separated prediction IDs to test (default: all 12)",
    )
    p_prove_agent.add_argument(
        "--csv",
        nargs="?",
        const="",
        default=None,
        help="Export results to CSV (default: results/agent/prediction_cross_validation.csv)",
    )
    p_prove_agent.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the response cache (each step calls the backend)",
    )
    p_prove_agent.add_argument(
        "--stub",
        action="store_true",
        help="Use deterministic StubBackend (CI mode, no API key)",
    )
    p_prove_agent.set_defaults(func=cmd_prove_agent)

    p_adv = sub.add_parser("adversary", help="RL adversary experiment (needs torch+sb3)")
    p_adv.add_argument("forward_args", nargs=argparse.REMAINDER)
    p_adv.set_defaults(func=cmd_adversary)

    p_agent = sub.add_parser(
        "agent", help="Run the governed/ungoverned LLM agent validation benchmark"
    )
    p_agent.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="Number of seed pairs per scenario (default: 1)",
    )
    p_agent.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Steps per arm (default: 100)",
    )
    p_agent.add_argument(
        "--backend",
        choices=["stub", "pydanticai"],
        default="stub",
        help="Agent backend: deterministic stub (CI, no API key) or real LLM (default: stub)",
    )
    p_agent.add_argument(
        "--model",
        type=str,
        default=None,
        help="Provider-prefixed model string (default: $GOVERNANCE_LLM_MODEL or "
        "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free; OpenRouter free "
        "models use the :free suffix)",
    )
    p_agent.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature; 0.0 makes full runs deterministic (default: 0.0)",
    )
    p_agent.add_argument(
        "--cache",
        type=str,
        default="",
        help=f"Response cache directory (default: {DEFAULT_CACHE_DIR})",
    )
    p_agent.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the response cache (each step calls the backend)",
    )
    p_agent.set_defaults(func=cmd_agent)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if hasattr(args, "steps") and args.steps is not None and args.steps < 1:
        parser.error("--steps must be > 0")
    if hasattr(args, "seeds") and args.seeds is not None and args.seeds < 1:
        parser.error("--seeds must be > 0")
    args.func(args)


if __name__ == "__main__":
    main()
