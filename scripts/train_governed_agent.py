"""
Train PPO agents on GovernanceGridWorld with and without the Neural Parliament.

Usage:
    python scripts/train_governed_agent.py [--timesteps 50000] [--seeds 3]

Output:
    results/rl/governed_model.zip       Trained PPO with Parliament
    results/rl/ungoverned_model.zip     Trained PPO without Parliament
    results/rl/governed_metrics.csv     Per-rollout metrics (governed)
    results/rl/ungoverned_metrics.csv   Per-rollout metrics (ungoverned)
    results/rl/comparison_summary.csv   Aggregated comparison across seeds
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nomos.experiments.gym_env import GovernanceGridWorld
from src.nomos.experiments.rl_metrics import (
    compute_episode_metrics,
    step_record_from_info,
    summarize_episodes,
)


def make_env(governed: bool = True, seed: int = 42):
    def _init():
        return GovernanceGridWorld(
            parliament="default" if governed else None,
            size=10, seed=seed, poison_ratio=0.2,
            apple_count=8, max_steps=200,
        )
    return _init


def evaluate(env_fn, model, episodes: int = 10) -> dict:
    """Evaluate a trained model using the canonical metrics.

    Shares :mod:`src.nomos.experiments.rl_metrics` with ``rl_train`` so both
    entrypoints count violations, apples, and vetoes identically. Totals are
    summed across episodes; veto precision/recall are pooled over the run.
    """
    env = env_fn()
    episode_metrics = []
    for _ in range(episodes):
        obs, _ = env.reset()
        done = False
        records = []
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(int(action))
            done = terminated or truncated
            records.append(step_record_from_info(info))
        episode_metrics.append(compute_episode_metrics(records))
    env.close()

    summary = summarize_episodes(episode_metrics)
    return {
        "mean_reward": summary["avg_reward"],
        "std_reward": summary["std_reward"],
        "violations": sum(m.violations for m in episode_metrics),
        "apples": sum(m.apples for m in episode_metrics),
        "poison": sum(m.poison for m in episode_metrics),
        "vetoes": sum(m.vetoes for m in episode_metrics),
        "veto_precision": summary["veto_precision"],
        "veto_recall": summary["veto_recall"],
        "falsifications": sum(m.falsifications for m in episode_metrics),
    }


def train_agent(governed: bool, timesteps: int, seed: int) -> dict:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv

    label = "governed" if governed else "ungoverned"
    print(f"  Training {label} agent (seed={seed}, timesteps={timesteps})...")

    env_fn = make_env(governed=governed, seed=seed)
    vec_env = DummyVecEnv([env_fn])

    model = PPO(
        "MlpPolicy", vec_env, verbose=0, seed=seed,
        learning_rate=3e-4, n_steps=2048, batch_size=64,
        n_epochs=10, gamma=0.99, gae_lambda=0.95,
        clip_range=0.2, ent_coef=0.01,
    )

    rollout_metrics = []
    class LogCallback(BaseCallback):
        def __init__(self):
            super().__init__()
            self._step = 0
        def _on_step(self):
            self._step += 1
            if self._step % 10 == 0:
                env = self.training_env.envs[0]
                rollout_metrics.append({
                    "step": self.num_timesteps,
                    "total_reward": env._total_reward,
                    "violations": env._violations,
                    "veto_count": env._veto_count,
                    "apples": env._apples_collected,
                    "poison": env._total_poison_eaten,
                })
            return True

    model.learn(total_timesteps=timesteps, callback=LogCallback(), progress_bar=False)

    os.makedirs("results/rl", exist_ok=True)
    model.save(f"results/rl/{label}_model.zip")

    eval_result = evaluate(env_fn, model, episodes=10)

    os.makedirs("results/rl", exist_ok=True)
    with open(f"results/rl/{label}_metrics.csv", "w", newline="") as f:
        if rollout_metrics:
            w = csv.DictWriter(f, fieldnames=rollout_metrics[0].keys())
            w.writeheader()
            w.writerows(rollout_metrics)

    result = {
        "label": label,
        "seed": seed,
        "mean_reward": round(eval_result["mean_reward"], 2),
        "std_reward": round(eval_result["std_reward"], 2),
        "eval_violations": eval_result["violations"],
        "eval_apples": eval_result["apples"],
        "eval_poison": eval_result["poison"],
        "eval_vetoes": eval_result["vetoes"],
        "eval_veto_precision": round(eval_result["veto_precision"], 3),
        "eval_veto_recall": round(eval_result["veto_recall"], 3),
        "eval_falsifications": eval_result["falsifications"],
    }
    vec_env.close()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=50000)
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()

    all_results = []
    for seed in range(args.seeds):
        for governed in [True, False]:
            r = train_agent(governed=governed, timesteps=args.timesteps, seed=seed)
            all_results.append(r)

    summary_path = "results/rl/comparison_summary.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_results[0].keys())
        w.writeheader()
        w.writerows(all_results)

    print()
    print("=== Evaluation Summary (10 episodes each) ===")
    print(f"  {'Condition':12s} {'MeanReward':>10s} {'StdReward':>9s}  "
          f"{'Viol':>4s} {'Apple':>5s} {'Poison':>6s} {'Veto':>4s}")
    for r in all_results:
        print(f"  {r['label']:12s} {r['mean_reward']:10.1f} {r['std_reward']:9.2f}  "
              f"{r['eval_violations']:4d} {r['eval_apples']:5d} "
              f"{r['eval_poison']:6d} {r['eval_vetoes']:4d}")

    gov = [r for r in all_results if r["label"] == "governed"]
    ung = [r for r in all_results if r["label"] == "ungoverned"]
    if gov and ung:
        g_mean = np.mean([r["mean_reward"] for r in gov])
        u_mean = np.mean([r["mean_reward"] for r in ung])
        g_viol = sum(r["eval_violations"] for r in gov)
        u_viol = sum(r["eval_violations"] for r in ung)
        print(f"\n  Governed avg reward:   {g_mean:.1f}  total violations: {g_viol}")
        print(f"  Ungoverned avg reward: {u_mean:.1f}  total violations: {u_viol}")


if __name__ == "__main__":
    main()
