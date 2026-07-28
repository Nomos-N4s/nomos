"""
train_minigrid.py — Train PPO agents on governed Minigrid environments.

Compares governed (Parliament active) vs ungoverned (no Parliament) agents
across multiple Minigrid environments.

Usage:
    python scripts/train_minigrid.py --env MiniGrid-Empty-8x8-v0 --timesteps 50000 --seeds 3
    python scripts/train_minigrid.py --env MiniGrid-DoorKey-8x8-v0 --timesteps 100000 --seeds 3
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from governance.experiments.minigrid_wrapper import GovernedMinigridWrapper


class _MinigridObsWrapper(gym.ObservationWrapper):
    """Drop 'mission' string field, flatten image+direction into a 1D Box."""

    def __init__(self, env):
        super().__init__(env)
        img_shape = env.observation_space.spaces["image"].shape
        flat_dim = int(np.prod(img_shape)) + 1  # image + direction (1 scalar)
        self.observation_space = spaces.Box(
            low=0, high=255, shape=(flat_dim,), dtype=np.float32,
        )

    def observation(self, obs):
        image = obs["image"].astype(np.float32).flatten()
        direction = np.array([obs["direction"]], dtype=np.float32)
        return np.concatenate([image, direction])


class MetricsCallback(BaseCallback):
    """Log per-episode metrics during training."""

    def __init__(self, csv_path: str):
        super().__init__()
        self.csv_path = csv_path
        self._episode_rewards: list[float] = []
        self._episode_lengths: list[float] = []
        self._current_reward = 0.0
        self._current_length = 0
        self._rows: list[dict] = []
        self._first = True

    def _on_step(self) -> bool:
        self._current_reward += self.locals["rewards"][0]
        self._current_length += 1
        if self.locals["dones"][0]:
            self._rows.append({
                "step": self.num_timesteps,
                "total_reward": round(self._current_reward, 2),
                "episode_length": self._current_length,
            })
            self._current_reward = 0.0
            self._current_length = 0
        return True

    def save(self):
        with open(self.csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["step", "total_reward", "episode_length"])
            w.writeheader()
            w.writerows(self._rows)


def evaluate(env, model, episodes: int = 10) -> dict:
    """Evaluate a trained model over multiple episodes."""
    rewards = []
    lengths = []
    for _ in range(episodes):
        obs, _ = env.reset()
        done = False
        ep_reward = 0.0
        ep_len = 0
        while not done and ep_len < 500:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, term, trunc, info = env.step(action)
            done = term or trunc
            ep_reward += reward
            ep_len += 1
        rewards.append(ep_reward)
        lengths.append(ep_len)

    m = {}
    for obj in [env, getattr(env, "env", None)]:
        if obj is not None and hasattr(obj, "metrics"):
            m = obj.metrics
            break
    return {
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_length": float(np.mean(lengths)),
        "total_vetoes": m.get("veto_count", 0),
        "total_violations": m.get("violations", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Train PPO on governed Minigrid environments")
    parser.add_argument("--env", default="MiniGrid-Empty-8x8-v0", help="Minigrid environment ID")
    parser.add_argument("--timesteps", type=int, default=50000, help="Total timesteps per condition")
    parser.add_argument("--seeds", type=int, default=3, help="Number of random seeds")
    parser.add_argument("--output-dir", default="results/rl/minigrid", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    env_short = args.env.replace("MiniGrid-", "").replace("-v0", "")

    # Always steps that actually train the model
    import gymnasium as gym
    import minigrid  # noqa: F401

    rows = []
    for seed in range(args.seeds):
        for label in ["governed", "ungoverned"]:
            print(f"\n  Training {label} agent (seed={seed}, env={args.env})...")

            base_env = gym.make(args.env)
            # Strip mission (string, not embeddable) and flatten to 1D Box
            base_env = _MinigridObsWrapper(base_env)
            env = GovernedMinigridWrapper(base_env) if label == "governed" else base_env

            # Wrap for SB3 (capture env by value using default arg)
            from stable_baselines3.common.env_util import make_vec_env
            vec_env = make_vec_env(lambda e=env: e, n_envs=1)

            csv_path = os.path.join(args.output_dir, f"{label}_{env_short}_seed{seed}.csv")
            cb = MetricsCallback(csv_path)

            model = PPO("MlpPolicy", vec_env,
                verbose=0, seed=seed,
                n_steps=1024, batch_size=64,
                policy_kwargs=dict(net_arch=[64, 64]),
            )
            model.learn(total_timesteps=args.timesteps, callback=cb)
            cb.save()

            # Save model
            model_path = os.path.join(args.output_dir, f"{label}_{env_short}_seed{seed}.zip")
            model.save(model_path)

            # Evaluate
            eval_env = gym.make(args.env)
            eval_env = _MinigridObsWrapper(eval_env)
            if label == "governed":
                eval_env = GovernedMinigridWrapper(eval_env)
            eval_results = evaluate(eval_env, model, episodes=10)
            eval_env.close()

            row = {
                "label": label,
                "env": env_short,
                "seed": seed,
                "timesteps": args.timesteps,
                "mean_reward": eval_results["mean_reward"],
                "std_reward": eval_results["std_reward"],
                "mean_episode_length": eval_results["mean_length"],
                "eval_vetoes": eval_results["total_vetoes"],
            }
            rows.append(row)
            print(f"    Mean reward: {eval_results['mean_reward']:.2f} (+-{eval_results['std_reward']:.2f})")

    # Write comparison summary
    summary_path = os.path.join(args.output_dir, "comparison_summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n=== {args.env} Comparison ===")
    print(f"  {'Seed':>5s} {'Gov Reward':>12s} {'Ungov Reward':>13s}")
    print(f"  {'-'*32}")
    for seed in range(args.seeds):
        gr = [r for r in rows if r["label"] == "governed" and r["seed"] == seed]
        ur = [r for r in rows if r["label"] == "ungoverned" and r["seed"] == seed]
        if gr and ur:
            print(f"  {seed:>5d} {gr[0]['mean_reward']:>12.2f} {ur[0]['mean_reward']:>13.2f}")

    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()
