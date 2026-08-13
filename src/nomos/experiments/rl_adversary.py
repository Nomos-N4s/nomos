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

from .rl_train import benchmark, evaluate, make_env, train_ppo


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
    )

    def verdict(value):
        return {True: "PASS", False: "FAIL", None: "n/a"}[value]

    print(f"\nAdversarial protocol ({len(seeds)} seeds, reward_mode={args.reward_mode}):")
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
    p_proto.set_defaults(func=cmd_protocol)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
