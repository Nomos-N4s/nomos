"""
PPO training harness for GovernanceGridWorld (requires stable-baselines3).

Trains a PPO agent under one of three modes:

- **governance** — Parliament filters actions via full committee deliberation
- **no_governance** — Actions go directly to the environment (no oversight)
- **static_mask** — Poison actions are statically blocked (simple filter)

Exports trained model + evaluation logs for the Streamlit dashboard.
"""

import json
import os
import time
from typing import Any

import numpy as np

from .gym_env import GovernanceGridWorld


def make_env(
    mode: str = "governance",
    size: int = 10,
    seed: int = 42,
    poison_ratio: float = 0.2,
    apple_count: int = 8,
    max_steps: int = 200,
    live_log_path: str | None = None,
) -> GovernanceGridWorld:
    """Create a :class:`~.gym_env.GovernanceGridWorld` instance.

    Args:
        mode: ``"governance"`` (default), ``"no_governance"``, or ``"static_mask"``.
        size: Grid dimension.
        seed: Random seed.
        poison_ratio: Fraction of tiles that are poison.
        apple_count: Number of apples to place.
        max_steps: Episode length limit.
        live_log_path: Optional path for JSONL step logging.

    Returns:
        A configured :class:`~.gym_env.GovernanceGridWorld`.
    """
    parliament = None if mode == "no_governance" else "default"  # sentinel: __init__ resolves it
    return GovernanceGridWorld(
        parliament=parliament,
        size=size,
        seed=seed,
        poison_ratio=poison_ratio,
        apple_count=apple_count,
        max_steps=max_steps,
        live_log_path=live_log_path,
    )


def evaluate(
    env: GovernanceGridWorld,
    model,
    episodes: int = 5,
    deterministic: bool = True,
) -> dict[str, Any]:
    """Evaluate a trained PPO model for a number of episodes.

    Args:
        env: The GovernanceGridWorld environment.
        model: A trained stable-baselines3 ``PPO`` model.
        episodes: Number of evaluation episodes.
        deterministic: Whether to use deterministic action selection.

    Returns:
        Dict with ``metrics_per_episode``, ``avg_reward``, ``std_reward``,
        ``avg_violations``, ``avg_apples``, ``total_steps``, and
        ``decision_history``.
    """
    metrics_list = []
    all_histories = []

    for ep in range(episodes):
        obs, _ = env.reset(seed=42 + ep)
        ep_reward = 0.0
        ep_violations = 0
        ep_steps = 0
        ep_apples = 0

        while True:
            action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(int(action))
            ep_reward += reward
            ep_violations += info["violations"]
            ep_apples += 1 if info.get("reward", 0) > 0.5 else 0
            ep_steps += 1

            if terminated or truncated:
                break

        metrics_list.append(
            {
                "episode": ep,
                "reward": ep_reward,
                "steps": ep_steps,
                "violations": ep_violations,
                "apples": ep_apples,
            }
        )
        all_histories.extend(env.decision_history)

    avg_reward = np.mean([m["reward"] for m in metrics_list])
    std_reward = np.std([m["reward"] for m in metrics_list])
    avg_violations = np.mean([m["violations"] for m in metrics_list])
    avg_apples = np.mean([m["apples"] for m in metrics_list])

    return {
        "metrics_per_episode": metrics_list,
        "avg_reward": float(avg_reward),
        "std_reward": float(std_reward),
        "avg_violations": float(avg_violations),
        "avg_apples": float(avg_apples),
        "total_steps": sum(m["steps"] for m in metrics_list),
        "decision_history": all_histories[:500],
    }


def train_ppo(
    mode: str = "governance",
    total_timesteps: int = 100_000,
    size: int = 10,
    seed: int = 42,
    log_dir: str = "results",
    live_log: bool = True,
    eval_episodes: int = 10,
) -> dict[str, Any]:
    """Train a PPO agent on GovernanceGridWorld.

    Saves the trained model and evaluation results to ``log_dir``.

    Args:
        mode: ``"governance"``, ``"no_governance"``, or ``"static_mask"``.
        total_timesteps: Number of training timesteps.
        size: Grid dimension.
        seed: Random seed.
        log_dir: Output directory for model, logs, and results.
        live_log: Whether to write a live JSONL step log.
        eval_episodes: Number of evaluation episodes after training.

    Returns:
        Dict with ``mode``, ``total_timesteps``, ``train_time_seconds``,
        ``model_path``, ``eval`` results, and ``training_log``.
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.callbacks import BaseCallback
    except ImportError:
        raise ImportError("stable-baselines3 not installed. Install with: uv sync --extra rl")

    class LogCallback(BaseCallback):
        def __init__(self, log_path: str):
            super().__init__()
            self.log_path = log_path
            self.timesteps_logged = []
            self.rewards_logged = []

        def _on_step(self) -> bool:
            if self.num_timesteps % 1000 == 0:
                self.timesteps_logged.append(self.num_timesteps)
                if len(self.locals.get("ep_info_buffer", [])) > 0:
                    avg = np.mean([ep.r for ep in self.locals["ep_info_buffer"]])
                    self.rewards_logged.append(float(avg))
                else:
                    self.rewards_logged.append(0.0)
            return True

    live_path = os.path.join(log_dir, f"live_{mode}.jsonl") if live_log else None
    env = make_env(mode=mode, size=size, seed=seed, live_log_path=live_path)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        seed=seed,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        learning_rate=3e-4,
    )

    callback = LogCallback(os.path.join(log_dir, f"train_log_{mode}.json"))
    t0 = time.time()
    model.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=False,
    )
    train_time = time.time() - t0

    model_path = os.path.join(log_dir, f"ppo_{mode}.zip")
    model.save(model_path)

    eval_env = make_env(mode=mode, size=size, seed=seed + 999)
    eval_results = evaluate(eval_env, model, episodes=eval_episodes)

    results = {
        "mode": mode,
        "total_timesteps": total_timesteps,
        "train_time_seconds": round(train_time, 1),
        "model_path": model_path,
        "eval": eval_results,
        "training_log": {
            "timesteps": callback.timesteps_logged,
            "avg_rewards": callback.rewards_logged,
        },
    }

    results_path = os.path.join(log_dir, f"results_{mode}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


def benchmark(
    total_timesteps: int = 100_000,
    size: int = 10,
    seeds: list[int] = None,
    log_dir: str = "results",
    eval_episodes: int = 10,
) -> dict[str, Any]:
    seeds = seeds or [42]
    all_results = {}

    for mode in ["governance", "no_governance"]:
        mode_results = []
        for seed in seeds:
            print(f"  Training {mode} with seed={seed}...")
            result = train_ppo(
                mode=mode,
                total_timesteps=total_timesteps,
                size=size,
                seed=seed,
                log_dir=log_dir,
                live_log=False,
                eval_episodes=eval_episodes,
            )
            mode_results.append(result["eval"])
        avg = np.mean([r["avg_reward"] for r in mode_results])
        std = np.std([r["avg_reward"] for r in mode_results])
        avg_v = np.mean([r["avg_violations"] for r in mode_results])
        all_results[mode] = {
            "avg_reward": float(avg),
            "std_reward": float(std),
            "avg_violations": float(avg_v),
            "n_seeds": len(seeds),
            "eval_results": mode_results,
        }

    benchmark_path = os.path.join(log_dir, "benchmark_results.json")
    with open(benchmark_path, "w") as f:
        json.dump(all_results, f, indent=2)

    return all_results
