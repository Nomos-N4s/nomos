"""
plot_minigrid_comparison.py — Plot governed vs ungoverned comparison on Minigrid environments.

Usage:
    python scripts/plot_minigrid_comparison.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def load_summary(path: str) -> list:
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found.")
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def load_metrics(label: str, env: str, seed: int, base_dir: str) -> list:
    path = os.path.join(base_dir, f"{label}_{env}_seed{seed}.csv")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def plot_comparison():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    base_dir = "results/rl/minigrid"
    summary = load_summary(os.path.join(base_dir, "comparison_summary.csv"))
    if not summary:
        print("No summary found. Run scripts/train_minigrid.py first.")
        return

    os.makedirs("results/figures", exist_ok=True)

    # Group by environment
    envs = sorted(set(r["env"] for r in summary))
    env_count = len(envs)
    fig, axes = plt.subplots(env_count, 2, figsize=(14, 5 * env_count))
    if env_count == 1:
        axes = axes.reshape(1, 2)

    for ei, env_name in enumerate(envs):
        erows = [r for r in summary if r["env"] == env_name]
        seeds = sorted(set(int(r["seed"]) for r in erows))

        # Left: bar chart of mean reward by seed
        ax = axes[ei, 0]
        x = np.arange(len(seeds))
        width = 0.35
        gov_means = []
        ung_means = []
        for s in seeds:
            gr = [r for r in erows if r["label"] == "governed" and int(r["seed"]) == s]
            ur = [r for r in erows if r["label"] == "ungoverned" and int(r["seed"]) == s]
            gov_means.append(float(gr[0]["mean_reward"]) if gr else 0)
            ung_means.append(float(ur[0]["mean_reward"]) if ur else 0)

        ax.bar(x - width/2, gov_means, width, label="Governed")
        ax.bar(x + width/2, ung_means, width, label="Ungoverned")
        ax.set_xlabel("Seed")
        ax.set_ylabel("Mean Episode Reward")
        ax.set_title(f"{env_name}: Mean Reward by Seed")
        ax.set_xticks(x)
        ax.set_xticklabels([str(s) for s in seeds])
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Right: veto counts
        ax = axes[ei, 1]
        gov_vetoes = []
        ung_vetoes = []
        for s in seeds:
            gr = [r for r in erows if r["label"] == "governed" and int(r["seed"]) == s]
            ur = [r for r in erows if r["label"] == "ungoverned" and int(r["seed"]) == s]
            gov_vetoes.append(int(gr[0]["eval_vetoes"]) if gr else 0)
            ung_vetoes.append(int(ur[0]["eval_vetoes"]) if ur else 0)

        ax.bar(x - width/2, gov_vetoes, width, label="Governed", color="purple")
        ax.bar(x + width/2, ung_vetoes, width, label="Ungoverned", color="gray")
        ax.set_xlabel("Seed")
        ax.set_ylabel("Total Vetoes (10 eval episodes)")
        ax.set_title(f"{env_name}: Parliament Vetoes by Seed")
        ax.set_xticks(x)
        ax.set_xticklabels([str(s) for s in seeds])
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = "results/figures/minigrid_comparison.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

    # Print aggregate table
    print(f"\n=== Minigrid Comparison Summary ===")
    print(f"  {'Env':20s} {'Seed':>5s} {'Gov Reward':>12s} {'Ungov Reward':>13s} {'Gov Vetoes':>10s}")
    print(f"  {'-'*62}")
    for env_name in envs:
        erows = [r for r in summary if r["env"] == env_name]
        seeds = sorted(set(int(r["seed"]) for r in erows))
        for s in seeds:
            gr = [r for r in erows if r["label"] == "governed" and int(r["seed"]) == s]
            ur = [r for r in erows if r["label"] == "ungoverned" and int(r["seed"]) == s]
            gr_reward = f"{float(gr[0]['mean_reward']):.2f}" if gr else "N/A"
            ur_reward = f"{float(ur[0]['mean_reward']):.2f}" if ur else "N/A"
            gr_vetoes = gr[0]["eval_vetoes"] if gr else "N/A"
            print(f"  {env_name:20s} {s:>5d} {gr_reward:>12s} {ur_reward:>13s} {gr_vetoes:>10s}")


if __name__ == "__main__":
    plot_comparison()
