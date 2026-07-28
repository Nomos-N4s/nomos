"""
train_safety_grid.py — Train PPO agents on SafetyGridWorld with cost constraints.

Compares governed (Parliament blocks hazard approaches) vs ungoverned.

Usage:
    python scripts/train_safety_grid.py --timesteps 50000 --seeds 3
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env

from governance.experiments.safety_grid_world import SafetyGridWorld


class MetricsCallback(BaseCallback):
    def __init__(self, csv_path: str):
        super().__init__()
        self.csv_path = csv_path
        self._episode_rewards = []
        self._episode_costs = []
        self._current_reward = 0.0
        self._current_cost = 0.0
        self._current_length = 0
        self._rows = []

    def _on_step(self) -> bool:
        self._current_reward += self.locals["rewards"][0]
        self._current_length += 1
        info = self.locals.get("infos", [{}])[0]
        self._current_cost += info.get("cost", 0.0)
        if self.locals["dones"][0]:
            self._rows.append({
                "step": self.num_timesteps,
                "total_reward": round(self._current_reward, 4),
                "total_cost": round(self._current_cost, 4),
                "episode_length": self._current_length,
            })
            self._current_reward = 0.0
            self._current_cost = 0.0
            self._current_length = 0
        return True

    def save(self):
        with open(self.csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["step", "total_reward", "total_cost", "episode_length"])
            w.writeheader()
            w.writerows(self._rows)


def evaluate(env, model, episodes: int = 10) -> dict:
    rewards, costs, lengths = [], [], []
    for _ in range(episodes):
        obs, _ = env.reset()
        done = False
        ep_reward, ep_cost, ep_len = 0.0, 0.0, 0
        while not done and ep_len < 500:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, term, trunc, info = env.step(action)
            done = term or trunc
            ep_reward += reward
            ep_cost += info.get("cost", 0.0)
            ep_len += 1
        rewards.append(ep_reward)
        costs.append(ep_cost)
        lengths.append(ep_len)

    return {
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_cost": float(np.mean(costs)),
        "mean_length": float(np.mean(lengths)),
    }


def main():
    parser = argparse.ArgumentParser(description="Train PPO on SafetyGridWorld")
    parser.add_argument("--timesteps", type=int, default=50000)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--num-hazards", type=int, default=5)
    parser.add_argument("--output-dir", default="results/rl/safety_grid")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    rows = []
    for seed in range(args.seeds):
        for label in ["governed", "ungoverned"]:
            print(f"\n  Training {label} agent (seed={seed})...")

            def make_env(label=label, seed=seed):
                parliament = None if label == "ungoverned" else "default"
                return SafetyGridWorld(parliament=parliament, seed=seed, num_hazards=args.num_hazards)

            venv = make_vec_env(lambda lab=label, s=seed: make_env(lab, s), n_envs=1)

            csv_path = os.path.join(args.output_dir, f"{label}_seed{seed}.csv")
            cb = MetricsCallback(csv_path)

            model = PPO("MlpPolicy", venv, verbose=0, seed=seed,
                        n_steps=1024, batch_size=64,
                        policy_kwargs=dict(net_arch=[64, 64]))
            model.learn(total_timesteps=args.timesteps, callback=cb)
            cb.save()

            model_path = os.path.join(args.output_dir, f"{label}_seed{seed}.zip")
            model.save(model_path)

            # Evaluate on a fresh env
            eval_env = SafetyGridWorld(
                parliament="default" if label == "governed" else None,
                seed=999, num_hazards=args.num_hazards,
            )
            eval_results = evaluate(eval_env, model, episodes=10)
            eval_env = None

            row = {
                "label": label,
                "seed": seed,
                "timesteps": args.timesteps,
                "num_hazards": args.num_hazards,
                "mean_reward": eval_results["mean_reward"],
                "std_reward": eval_results["std_reward"],
                "mean_cost": eval_results["mean_cost"],
                "mean_episode_length": eval_results["mean_length"],
            }
            rows.append(row)
            print(f"    reward={row['mean_reward']:.3f} cost={row['mean_cost']:.3f}")

    summary_path = os.path.join(args.output_dir, "comparison_summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n=== SafetyGridWorld Comparison ===")
    print(f"  {'Seed':>5s} {'Gov Reward':>12s} {'Ungov Reward':>13s} {'Gov Cost':>10s} {'Ungov Cost':>11s}")
    print(f"  {'-'*53}")
    for seed in range(args.seeds):
        gr = [r for r in rows if r["label"] == "governed" and r["seed"] == seed]
        ur = [r for r in rows if r["label"] == "ungoverned" and r["seed"] == seed]
        if gr and ur:
            print(f"  {seed:>5d} {gr[0]['mean_reward']:>12.4f} {ur[0]['mean_reward']:>13.4f} {gr[0]['mean_cost']:>10.4f} {ur[0]['mean_cost']:>11.4f}")
    print(f"\nSaved: {summary_path}")


if __name__ == "__main__":
    main()
