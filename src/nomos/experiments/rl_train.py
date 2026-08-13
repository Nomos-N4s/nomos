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
from .rl_metrics import (
    compute_episode_metrics,
    step_record_from_info,
    summarize_episodes,
)

#: The governance modes that actually exist as distinct code paths.
MODES = ("governance", "no_governance", "static_mask")


def make_env(
    mode: str = "governance",
    size: int = 10,
    seed: int = 42,
    poison_ratio: float = 0.2,
    apple_count: int = 8,
    max_steps: int = 200,
    live_log_path: str | None = None,
    adversarial: bool = False,
    reward_mode: str = "task",
) -> GovernanceGridWorld:
    """Create a :class:`~.gym_env.GovernanceGridWorld` instance.

    Args:
        mode: One of :data:`MODES` — ``"governance"`` (full Parliament),
            ``"no_governance"`` (actions execute directly), or ``"static_mask"``
            (a fixed filter blocks poison moves, no Parliament).
        size: Grid dimension.
        seed: Random seed.
        poison_ratio: Fraction of tiles that are poison.
        apple_count: Number of apples to place.
        max_steps: Episode length limit.
        live_log_path: Optional path for JSONL step logging.
        adversarial: When ``True`` the policy gets the composite attack-surface
            action space (forge tag, mis-report risk/coherence, flood proposals).
            Defaults to ``False`` (honest mode), reproducing the original
            benchmark behaviour.
        reward_mode: ``"task"`` (default) or ``"bypass"`` — see
            :class:`~.gym_env.GovernanceGridWorld`.

    Returns:
        A configured :class:`~.gym_env.GovernanceGridWorld`.

    Raises:
        ValueError: If ``mode`` is not one of :data:`MODES`.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")
    parliament = "default" if mode == "governance" else None  # sentinel: __init__ resolves it
    return GovernanceGridWorld(
        parliament=parliament,
        size=size,
        seed=seed,
        poison_ratio=poison_ratio,
        apple_count=apple_count,
        max_steps=max_steps,
        adversarial=adversarial,
        reward_mode=reward_mode,
        live_log_path=live_log_path,
        static_mask=(mode == "static_mask"),
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
        ``avg_violations``, ``avg_apples``, ``avg_vetoes``, ``veto_precision``,
        ``veto_recall``, ``avg_falsifications``, ``total_steps``, and
        ``decision_history``. All counts follow the canonical definitions in
        :mod:`nomos.experiments.rl_metrics`.
    """
    episode_metrics = []
    metrics_list = []
    all_histories = []

    for ep in range(episodes):
        obs, _ = env.reset(seed=42 + ep)
        records = []

        while True:
            action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            records.append(step_record_from_info(info))

            if terminated or truncated:
                break

        em = compute_episode_metrics(records)
        episode_metrics.append(em)
        metrics_list.append({"episode": ep, **em.as_dict()})
        all_histories.extend(env.decision_history)

    summary = summarize_episodes(episode_metrics)

    return {
        "metrics_per_episode": metrics_list,
        "avg_reward": summary["avg_reward"],
        "std_reward": summary["std_reward"],
        "avg_violations": summary["avg_violations"],
        "avg_apples": summary["avg_apples"],
        "avg_vetoes": summary["avg_vetoes"],
        "veto_precision": summary["veto_precision"],
        "veto_recall": summary["veto_recall"],
        "avg_falsifications": summary["avg_falsifications"],
        "total_steps": summary["total_steps"],
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
    modes: list[str] | None = None,
) -> dict[str, Any]:
    """Train and evaluate across governance modes and seeds.

    Args:
        total_timesteps: Training steps per (mode, seed) run.
        size: Grid dimension.
        seeds: Seeds to average over (defaults to ``[42]``).
        log_dir: Output directory.
        eval_episodes: Evaluation episodes per run.
        modes: Modes to benchmark. Defaults to :data:`MODES` — exactly the
            modes that exist as distinct code paths.

    Returns:
        Per-mode aggregate statistics, also written to
        ``benchmark_results.json``.
    """
    seeds = seeds or [42]
    modes = modes or list(MODES)
    for mode in modes:
        if mode not in MODES:
            raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")
    all_results = {}

    for mode in modes:
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
        all_results[mode] = {
            "avg_reward": float(np.mean([r["avg_reward"] for r in mode_results])),
            "std_reward": float(np.std([r["avg_reward"] for r in mode_results])),
            "avg_violations": float(np.mean([r["avg_violations"] for r in mode_results])),
            "avg_apples": float(np.mean([r["avg_apples"] for r in mode_results])),
            "avg_vetoes": float(np.mean([r["avg_vetoes"] for r in mode_results])),
            "veto_precision": float(np.mean([r["veto_precision"] for r in mode_results])),
            "veto_recall": float(np.mean([r["veto_recall"] for r in mode_results])),
            "n_seeds": len(seeds),
            "eval_results": mode_results,
        }

    benchmark_path = os.path.join(log_dir, "benchmark_results.json")
    with open(benchmark_path, "w") as f:
        json.dump(all_results, f, indent=2)

    return all_results
