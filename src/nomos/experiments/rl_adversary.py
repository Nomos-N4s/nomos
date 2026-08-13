"""
CLI entry point for the RL adversary experiment.

Provides three subcommands:

- **train**: Train a PPO agent (governed or ungoverned)
- **eval**: Evaluate a trained model on the environment
- **benchmark**: Run comparison across multiple seeds

Requires ``stable-baselines3`` (install with ``uv sync --extra rl``).

Usage:
  ``python -m src.nomos.experiments.rl_adversary train --mode governance --timesteps 100000``
  ``python -m src.nomos.experiments.rl_adversary benchmark --timesteps 100000 --seeds 42 43 44``
  ``python -m src.nomos.experiments.rl_adversary eval --model results/ppo_nomos.zip --episodes 5``
"""

import argparse
import sys

from .gym_env import DEFAULT_CLAIM_RESOLUTION
from .rl_sweep import SWEEP_AMBIGUITY_RATIO, SWEEP_CLAIM_RESOLUTION
from .rl_train import benchmark, evaluate, make_env, train_ppo
from .rl_verifier import DEFAULT_SENSOR_NOISE, VERIFIER_KINDS


def cmd_train(args):
    result = train_ppo(
        mode=args.mode,
        total_timesteps=args.timesteps,
        size=args.size,
        seed=args.seed,
        log_dir=args.log_dir,
        eval_episodes=args.eval_episodes,
    )
    e = result["eval"]
    print(f"\nTraining complete: {args.mode}")
    print(f"  Total timesteps: {args.timesteps}")
    print(f"  Train time: {result['train_time_seconds']}s")
    print(f"  Eval avg reward: {e['avg_reward']:.2f} ± {e['std_reward']:.2f}")
    print(f"  Eval avg violations: {e['avg_violations']:.2f}")
    print(f"  Eval avg apples: {e['avg_apples']:.1f}")
    print(f"  Model saved to: {result['model_path']}")


def cmd_eval(args):
    try:
        from stable_baselines3 import PPO
    except ImportError:
        print("stable-baselines3 not installed. Run: uv sync --extra rl")
        sys.exit(1)

    model = PPO.load(args.model)
    env = make_env(mode=args.mode, size=args.size, seed=42, live_log_path=args.live_log)
    result = evaluate(env, model, episodes=args.episodes)
    print(f"\nEvaluation: {args.mode}")
    print(f"  Episodes: {args.episodes}")
    print(f"  Avg reward: {result['avg_reward']:.2f} ± {result['std_reward']:.2f}")
    print(f"  Avg violations: {result['avg_violations']:.2f}")
    print(f"  Avg apples: {result['avg_apples']:.1f}")


def cmd_benchmark(args):
    seeds = args.seeds if args.seeds else [42]
    results = benchmark(
        total_timesteps=args.timesteps,
        size=args.size,
        seeds=seeds,
        log_dir=args.log_dir,
        eval_episodes=args.eval_episodes,
    )
    print(f"\nBenchmark results ({len(seeds)} seeds):")
    for mode, data in results.items():
        print(f"  {mode}:")
        print(f"    avg_reward:    {data['avg_reward']:.2f} ± {data['std_reward']:.2f}")
        print(f"    avg_violations: {data['avg_violations']:.2f}")
    print(f"\nResults saved to {args.log_dir}/benchmark_results.json")


def cmd_protocol(args):
    from .rl_protocol import DEFAULT_SEEDS, run_protocol

    seeds = args.seeds if args.seeds else list(DEFAULT_SEEDS)
    modes = args.modes if args.modes else None
    aggregate = run_protocol(
        modes=modes,
        seeds=seeds,
        total_timesteps=args.timesteps,
        size=args.size,
        eval_episodes=args.eval_episodes,
        reward_mode=args.reward_mode,
        log_dir=args.log_dir,
        verifier_accuracy=args.verifier_accuracy,
        verifier_kind=args.verifier_kind,
        verifier_sensor_noise=args.verifier_sensor_noise,
        ambiguity_ratio=args.ambiguity_ratio,
        spoof_region=args.spoof_region,
        claim_resolution=args.claim_resolution,
        shaped=args.shaped,
    )

    def verdict(value):
        return {True: "PASS", False: "FAIL", None: "n/a"}[value]

    verifier = aggregate["protocol"]["verifier"]
    print(f"\nAdversarial protocol ({len(seeds)} seeds, reward_mode={args.reward_mode}):")
    print(
        f"  verifier: {verifier['kind']} (effective accuracy {verifier['effective_accuracy']:.4f})"
    )
    for mode, data in aggregate["results"].items():
        print(f"  {mode}:")
        print(
            f"    bypass_rate: {data['governance_bypass_rate']['mean']:.4f} "
            f"± {data['governance_bypass_rate']['ci95']:.4f}"
        )
        print(
            f"    H1={verdict(data['h1']['pass'])} "
            f"H2={verdict(data['h2']['pass'])} "
            f"H3={verdict(data['h3']['pass'])}"
        )
    print(f"\nResults saved to {args.log_dir}/adversary_protocol.json")


def cmd_sweep(args):
    from .rl_protocol import DEFAULT_SEEDS
    from .rl_sweep import (
        ARMS,
        EPSILON_GRID,
        assemble_frontier,
        run_controls,
        run_point,
        run_sweep,
    )

    seeds = args.seeds if args.seeds else list(DEFAULT_SEEDS)
    shared = {
        "seeds": seeds,
        "total_timesteps": args.timesteps,
        "size": args.size,
        "eval_episodes": args.eval_episodes,
        "ambiguity_ratio": args.ambiguity_ratio,
        "spoof_region": not args.no_spoof_region,
        "claim_resolution": args.claim_resolution,
        "log_dir": args.log_dir,
    }

    # Points are independent seeded runs, so running them as separate processes
    # is a scheduling detail. --point runs exactly one and stops; --assemble
    # rebuilds the curve from whatever points are on disk.
    if args.point:
        arm, epsilon = args.point
        run_point(arm=arm, epsilon=float(epsilon), **shared)
        print(f"Point {arm} eps={epsilon} written to {args.log_dir}")
        return
    if args.controls_only:
        run_controls(**shared)
        print(f"Controls written to {args.log_dir}/controls.json")
        return
    if args.assemble:
        frontier = assemble_frontier(args.log_dir)
    else:
        frontier = run_sweep(
            epsilons=args.epsilons if args.epsilons else EPSILON_GRID,
            arms=args.arms if args.arms else ARMS,
            controls=not args.no_controls,
            **shared,
        )

    def verdict(value):
        return {True: "PASS", False: "FAIL", None: "n/a"}[value]

    verdicts = frontier["verdicts"]
    shape = verdicts["curve_shape"]
    print("\nVerifier-quality frontier:")
    print(f"  {'arm':>9}  {'eps':>5}  {'bypass':>16}  {'detection':>10}  {'silenced':>9}")
    for point in frontier["points"]:
        rate = point["bypass_rate"]
        detection = (
            point["detection_rate"]["mean"] if point["detection_rate"]["n"] else float("nan")
        )
        silenced = (
            point["safety_silenced_rate"]["mean"]
            if point["safety_silenced_rate"]["n"]
            else float("nan")
        )
        print(
            f"  {point['arm']:>9}  {point['epsilon']:>5}  "
            f"{rate['mean']:.4f} +/- {rate['ci95']:.4f}  {detection:>10.4f}  {silenced:>9.4f}"
        )
    print(
        f"\n  H4={verdict(verdicts['h4']['pass'])} "
        f"H5={verdict(verdicts['h5']['pass'])} "
        f"H6={verdict(verdicts['h6']['pass'])} "
        f"H7={verdict(verdicts['h7']['pass'])}"
    )
    print(f"  curve shape: {'CLIFF' if shape['cliff'] else 'graceful'}")
    if shape["critical_epsilon_region"]:
        print(f"  critical-epsilon region: {shape['critical_epsilon_region']}")
    if verdicts["h6"]["pass"] is False:
        h6 = verdicts["h6"]
        ambiguous = h6.get("best_arm_ambiguous_bypass")
        print(
            f"\n  WARNING: H6 failed — overall bypass at epsilon={h6['epsilon']} is "
            f"{h6['best_arm_bypass']:.4f}, below the {h6['threshold']} winnability bar.\n"
            "  By the pre-registered rule, H4/H5 must therefore be read as uninformative."
        )
        # The overall rate is diluted by attempt composition, so it can fail while
        # the adversary was in fact winning. Printing only the pre-registered
        # reading would state something false whenever that happens.
        if ambiguous is not None:
            print(
                f"  On winnable (ambiguous) tiles alone the rate is {ambiguous:.4f}. "
                "Read both\n  before concluding the adversary could not play."
            )
    print(f"\nResults saved to {args.log_dir}/verifier_frontier.json")


def main():
    parser = argparse.ArgumentParser(description="RL Adversary against Nomos")
    sub = parser.add_subparsers(dest="command")

    p_train = sub.add_parser("train", help="Train PPO agent")
    p_train.add_argument(
        "--mode", choices=["governance", "no_governance", "static_mask"], default="governance"
    )
    p_train.add_argument("--timesteps", type=int, default=100_000)
    p_train.add_argument("--size", type=int, default=10)
    p_train.add_argument("--seed", type=int, default=42)
    p_train.add_argument("--log-dir", default="results")
    p_train.add_argument("--eval-episodes", type=int, default=10)
    p_train.set_defaults(func=cmd_train)

    p_eval = sub.add_parser("eval", help="Evaluate trained model")
    p_eval.add_argument("--model", required=True)
    p_eval.add_argument(
        "--mode", choices=["governance", "no_governance", "static_mask"], default="governance"
    )
    p_eval.add_argument("--size", type=int, default=10)
    p_eval.add_argument("--episodes", type=int, default=5)
    p_eval.add_argument("--live-log", type=str, help="Path for live JSONL log")
    p_eval.set_defaults(func=cmd_eval)

    p_bench = sub.add_parser(
        "benchmark", help="Benchmark governance vs no_governance vs static_mask"
    )
    p_bench.add_argument("--timesteps", type=int, default=100_000)
    p_bench.add_argument("--size", type=int, default=10)
    p_bench.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p_bench.add_argument("--log-dir", default="results")
    p_bench.add_argument("--eval-episodes", type=int, default=10)
    p_bench.set_defaults(func=cmd_benchmark)

    p_proto = sub.add_parser("protocol", help="Run the pre-registered adversarial H1-H3 protocol")
    p_proto.add_argument(
        "--modes",
        nargs="+",
        choices=["governance", "no_governance", "static_mask"],
        default=None,
        help="Modes to run (default: all three).",
    )
    p_proto.add_argument("--timesteps", type=int, default=100_000)
    p_proto.add_argument("--size", type=int, default=10)
    p_proto.add_argument("--seeds", type=int, nargs="+", default=None)
    p_proto.add_argument("--reward-mode", choices=["task", "bypass"], default="bypass")
    p_proto.add_argument("--eval-episodes", type=int, default=10)
    p_proto.add_argument("--log-dir", default="results/rl_adversary")
    p_proto.add_argument(
        "--verifier-accuracy",
        type=float,
        default=1.0,
        help=(
            "Integrity verifier accuracy epsilon in [0, 1]. 1.0 (default) is the "
            "oracle behind the published Appendix E run."
        ),
    )
    p_proto.add_argument(
        "--verifier-kind",
        choices=list(VERIFIER_KINDS),
        default="parametric",
        help="Parametric epsilon dial, or a learned classifier whose accuracy is measured.",
    )
    p_proto.add_argument(
        "--verifier-sensor-noise",
        type=float,
        default=DEFAULT_SENSOR_NOISE,
        help="Sensor noise-to-signal ratio for the learned verifier; ignored by the dial.",
    )
    p_proto.add_argument(
        "--ambiguity-ratio",
        type=float,
        default=0.0,
        help="Fraction of poison that is near-threshold ambiguous poison (default 0.0).",
    )
    p_proto.add_argument(
        "--spoof-region",
        action="store_true",
        help="Scale the falsification penalty by the size of the lie, making a spoof region exist.",
    )
    p_proto.add_argument(
        "--claim-resolution",
        type=int,
        default=DEFAULT_CLAIM_RESOLUTION,
        help="Number of claim buckets (default 3, the published granularity).",
    )
    arm = p_proto.add_mutually_exclusive_group()
    arm.add_argument(
        "--shaped",
        dest="shaped",
        action="store_true",
        help="Train with partial credit for progress against Integrity. Evaluation stays unshaped.",
    )
    arm.add_argument(
        "--unshaped",
        dest="shaped",
        action="store_false",
        help="Train on the unshaped bypass reward (default).",
    )
    p_proto.set_defaults(func=cmd_protocol, shaped=False)

    p_sweep = sub.add_parser(
        "sweep", help="Run the pre-registered epsilon-sweep and score H4-H7 (#275)"
    )
    p_sweep.add_argument(
        "--epsilons",
        type=float,
        nargs="+",
        default=None,
        help="Verifier accuracy grid (default: the pre-registered grid).",
    )
    p_sweep.add_argument(
        "--arms",
        nargs="+",
        choices=["unshaped", "shaped"],
        default=None,
        help="Training arms (default: both).",
    )
    p_sweep.add_argument("--seeds", type=int, nargs="+", default=None)
    p_sweep.add_argument("--timesteps", type=int, default=100_000)
    p_sweep.add_argument("--size", type=int, default=10)
    p_sweep.add_argument("--eval-episodes", type=int, default=10)
    p_sweep.add_argument("--ambiguity-ratio", type=float, default=SWEEP_AMBIGUITY_RATIO)
    p_sweep.add_argument("--claim-resolution", type=int, default=SWEEP_CLAIM_RESOLUTION)
    p_sweep.add_argument(
        "--no-spoof-region",
        action="store_true",
        help="Disable graded falsification severity (ablation: removes the reachable region).",
    )
    p_sweep.add_argument(
        "--no-controls",
        action="store_true",
        help="Skip the ceiling/floor control runs at the anchor epsilon.",
    )
    p_sweep.add_argument("--log-dir", default="results/rl_frontier")
    schedule = p_sweep.add_mutually_exclusive_group()
    schedule.add_argument(
        "--point",
        nargs=2,
        metavar=("ARM", "EPSILON"),
        default=None,
        help="Run exactly one (arm, epsilon) point and stop, for parallel scheduling.",
    )
    schedule.add_argument(
        "--controls-only",
        action="store_true",
        help="Run only the ceiling/floor controls at the anchor epsilon.",
    )
    schedule.add_argument(
        "--assemble",
        action="store_true",
        help="Rebuild the curve from the point artifacts already in --log-dir.",
    )
    p_sweep.set_defaults(func=cmd_sweep)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
