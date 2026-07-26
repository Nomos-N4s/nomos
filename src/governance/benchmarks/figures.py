"""
figures.py — Publication-ready comparison figures from benchmark results.

Generates:
  1. Reward curves over time (mean ± 95% CI shaded)
  2. Violation rate bar chart with error bars
  3. Deadlock frequency comparison (grouped bar)
  4. Pareto frontier: cumulative reward vs safety violations
"""

import os
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..experiments.metrics import ExperimentReport


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def plot_reward_curves(reports: List[ExperimentReport],
                       output_dir: str = "results/figures"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    _ensure_dir(f"{output_dir}/reward_curves.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("Reward Curves Over Time", fontsize=14, fontweight="bold")

    for idx, scenario in enumerate(scenarios):
        ax = axes[idx // 2][idx % 2]
        ax.set_title(scenario)

        for sidx, strategy in enumerate(strategies):
            relevant = [r for r in reports
                        if r.metadata.get("scenario") == scenario
                        and r.metadata.get("strategy") == strategy]
            if not relevant:
                continue

            all_curves = []
            for r in relevant:
                steps = r.metadata.get("step_records", [])
                curve = [s.get("reward", 0) for s in steps]
                if curve:
                    all_curves.append(curve)

            if not all_curves:
                continue

            min_len = min(len(c) for c in all_curves)
            aligned = [c[:min_len] for c in all_curves]

            means = [statistics.mean([c[i] for c in aligned]) for i in range(min_len)]
            stds = [statistics.stdev([c[i] for c in aligned]) if len(aligned) > 1 else 0
                    for i in range(min_len)]
            cis = [1.96 * s / (len(aligned) ** 0.5) if len(aligned) > 1 else 0
                   for s in stds]

            x = list(range(min_len))
            color = colors[sidx % len(colors)]
            ax.plot(x, means, label=strategy, color=color, linewidth=1.5)
            ax.fill_between(x, [m - c for m, c in zip(means, cis)],
                            [m + c for m, c in zip(means, cis)],
                            alpha=0.15, color=color)

        ax.set_xlabel("Step")
        ax.set_ylabel("Cumulative Reward")
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/reward_curves.png", dpi=150)
    plt.savefig(f"{output_dir}/reward_curves.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/reward_curves.png")


def plot_violation_rates(reports: List[ExperimentReport],
                          output_dir: str = "results/figures"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _ensure_dir(f"{output_dir}/violation_rates.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    x = np.arange(len(scenarios))
    width = 0.8 / max(len(strategies), 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Constraint Violation Rates by Scenario", fontsize=14, fontweight="bold")

    for sidx, strategy in enumerate(strategies):
        means = []
        errors = []
        for scenario in scenarios:
            relevant = [r for r in reports
                        if r.metadata.get("scenario") == scenario
                        and r.metadata.get("strategy") == strategy]
            if relevant:
                vals = [r.constraint_violations / max(r.total_steps, 1) for r in relevant]
                means.append(statistics.mean(vals))
                errors.append(statistics.stdev(vals) if len(vals) > 1 else 0)
            else:
                means.append(0)
                errors.append(0)

        offset = (sidx - len(strategies) / 2 + 0.5) * width
        ax.bar(x + offset, means, width, label=strategy,
               color=colors[sidx % len(colors)], yerr=errors, capsize=3)

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Violation Rate")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/violation_rates.png", dpi=150)
    plt.savefig(f"{output_dir}/violation_rates.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/violation_rates.png")


def plot_deadlock_frequency(reports: List[ExperimentReport],
                             output_dir: str = "results/figures"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _ensure_dir(f"{output_dir}/deadlock_frequency.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    x = np.arange(len(scenarios))
    width = 0.8 / max(len(strategies), 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Deadlock Frequency by Scenario", fontsize=14, fontweight="bold")

    for sidx, strategy in enumerate(strategies):
        means = []
        errors = []
        for scenario in scenarios:
            relevant = [r for r in reports
                        if r.metadata.get("scenario") == scenario
                        and r.metadata.get("strategy") == strategy]
            if relevant:
                vals = [r.deadlock_rate for r in relevant]
                means.append(statistics.mean(vals))
                errors.append(statistics.stdev(vals) if len(vals) > 1 else 0)
            else:
                means.append(0)
                errors.append(0)

        offset = (sidx - len(strategies) / 2 + 0.5) * width
        ax.bar(x + offset, means, width, label=strategy,
               color=colors[sidx % len(colors)], yerr=errors, capsize=3)

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Deadlock Rate")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/deadlock_frequency.png", dpi=150)
    plt.savefig(f"{output_dir}/deadlock_frequency.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/deadlock_frequency.png")


def plot_pareto_frontier(reports: List[ExperimentReport],
                          output_dir: str = "results/figures"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _ensure_dir(f"{output_dir}/pareto_frontier.png")

    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))
    markers = ["o", "s", "D", "^", "v"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Pareto Frontier: Reward vs Safety", fontsize=14, fontweight="bold")

    for sidx, strategy in enumerate(strategies):
        relevant = [r for r in reports
                    if r.metadata.get("strategy") == strategy]
        if not relevant:
            continue

        rewards = [r.total_reward for r in relevant]
        violations = [r.constraint_violations for r in relevant]
        ax.scatter(violations, rewards, label=strategy,
                   color=colors[sidx % len(colors)],
                   marker=markers[sidx % len(markers)],
                   alpha=0.6, s=40)

    ax.set_xlabel("Total Constraint Violations")
    ax.set_ylabel("Total Reward")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/pareto_frontier.png", dpi=150)
    plt.savefig(f"{output_dir}/pareto_frontier.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/pareto_frontier.png")


def generate_all_figures(reports: List[ExperimentReport],
                          output_dir: str = "results/figures"):
    print("Generating figures...")
    plot_reward_curves(reports, output_dir)
    plot_violation_rates(reports, output_dir)
    plot_deadlock_frequency(reports, output_dir)
    plot_pareto_frontier(reports, output_dir)
    print(f"All figures saved to {output_dir}/")


if __name__ == "__main__":
    from .run_all import run_gridworld_experiments, run_temptation_experiments
    from .run_all import run_drift_experiments, run_deadlock_experiments

    reports = []
    for runner, scenario in [
        (run_gridworld_experiments, "GridWorld"),
        (run_temptation_experiments, "TemptationBank"),
        (run_drift_experiments, "DriftLab"),
        (run_deadlock_experiments, "DeadlockMaze"),
    ]:
        reps = runner(steps=50, seeds=3,
                       strategies=["governance", "monolithic_rl", "random"])
        for r in reps:
            r.metadata["scenario"] = scenario
        reports.extend(reps)

    generate_all_figures(reports)