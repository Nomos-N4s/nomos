"""
Plot governed vs ungoverned RL comparison from training metrics.

Usage:
    python scripts/plot_rl_comparison.py

Requires: results/rl/comparison_summary.csv and results/rl/{governed,ungoverned}_metrics.csv
Produced by: scripts/train_governed_agent.py

Output: results/figures/rl_comparison.png (2x2 grid)
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def load_metrics(label: str) -> list:
    path = f"results/rl/{label}_metrics.csv"
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found. Run scripts/train_governed_agent.py first.")
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def load_summary() -> list:
    path = "results/rl/comparison_summary.csv"
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found.")
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

    gov = load_metrics("governed")
    ung = load_metrics("ungoverned")
    summary = load_summary()

    os.makedirs("results/figures", exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    if gov and ung:
        gov_steps = [int(r["step"]) for r in gov]
        gov_reward = [float(r["total_reward"]) for r in gov]
        ung_steps = [int(r["step"]) for r in ung]
        ung_reward = [float(r["total_reward"]) for r in ung]

        min_len = min(len(gov_steps), len(ung_steps))
        gov_steps = gov_steps[:min_len]
        gov_reward = gov_reward[:min_len]
        ung_steps = ung_steps[:min_len]
        ung_reward = ung_reward[:min_len]

        ax = axes[0, 0]
        ax.plot(gov_steps, gov_reward, label="Governed", alpha=0.8, linewidth=1.5)
        ax.plot(ung_steps, ung_reward, label="Ungoverned", alpha=0.8, linewidth=1.5)
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Cumulative Reward")
        ax.set_title("Reward Over Training")
        ax.legend()
        ax.grid(True, alpha=0.3)

        gov_viol = [int(r.get("violations", 0)) for r in gov]
        ung_viol = [int(r.get("violations", 0)) for r in ung]

        ax = axes[0, 1]
        ax.plot(gov_steps, gov_viol, label="Governed", alpha=0.8, linewidth=1.5)
        ax.plot(ung_steps, ung_viol, label="Ungoverned", alpha=0.8, linewidth=1.5)
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Constraint Violations")
        ax.set_title("Violations Over Training")
        ax.legend()
        ax.grid(True, alpha=0.3)

        gov_veto = [int(r.get("veto_count", 0)) for r in gov]
        ax = axes[1, 0]
        ax.plot(gov_steps, gov_veto, color="purple", alpha=0.8, linewidth=1.5)
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Veto Count")
        ax.set_title("Parliament Vetoes (Governed Only)")
        ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    if summary:
        gov_rows = [r for r in summary if r["label"] == "governed"]
        ung_rows = [r for r in summary if r["label"] == "ungoverned"]
        if gov_rows and ung_rows:
            labels = []
            gov_means = []
            ung_means = []
            for i in range(max(len(gov_rows), len(ung_rows))):
                labels.append(f"Seed {i}")
                if i < len(gov_rows):
                    gov_means.append(float(gov_rows[i]["mean_reward"]))
                if i < len(ung_rows):
                    ung_means.append(float(ung_rows[i]["mean_reward"]))

            x = np.arange(len(labels))
            width = 0.35
            if gov_means:
                ax.bar(x - width/2, gov_means, width, label="Governed")
            if ung_means:
                ax.bar(x + width/2, ung_means, width, label="Ungoverned")
            ax.set_xlabel("Seed")
            ax.set_ylabel("Mean Episode Reward")
            ax.set_title("Evaluation: Mean Reward by Seed")
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = "results/figures/rl_comparison.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

    if summary:
        print()
        print("=== Aggregated Comparison ===")
        gov_rows = [r for r in summary if r["label"] == "governed"]
        ung_rows = [r for r in summary if r["label"] == "ungoverned"]
        if gov_rows and ung_rows:
            g_mean = np.mean([float(r["mean_reward"]) for r in gov_rows])
            u_mean = np.mean([float(r["mean_reward"]) for r in ung_rows])
            g_viol = sum(int(r.get("eval_violations", 0)) for r in gov_rows)
            u_viol = sum(int(r.get("eval_violations", 0)) for r in ung_rows)
            g_apples = sum(int(r.get("eval_apples", 0)) for r in gov_rows)
            u_apples = sum(int(r.get("eval_apples", 0)) for r in ung_rows)
            print(f"  {'Metric':30s} {'Governed':>10s} {'Ungoverned':>10s}")
            print(f"  {'-'*52}")
            print(f"  {'Mean episode reward':30s} {g_mean:>10.2f} {u_mean:>10.2f}")
            print(f"  {'Total violations (eval)':30s} {g_viol:>10d} {u_viol:>10d}")
            print(f"  {'Total apples (eval)':30s} {g_apples:>10d} {u_apples:>10d}")


if __name__ == "__main__":
    plot_comparison()
