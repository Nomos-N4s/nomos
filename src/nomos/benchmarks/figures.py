"""
Publication-ready comparison figures from benchmark results.

Generates four publication-quality plots:

1. **Reward curves** — Mean cumulative reward over time with shaded 95% CI
   (bootstrap, from analysis pipeline).
2. **Violation rates** — Grouped bar chart per scenario-strategy with
   bootstrap CI error bars.
3. **Deadlock frequency** — Grouped bar chart of deadlock rates with
   bootstrap CI error bars.
4. **Pareto frontier** — Reward vs. safety violations with the convex
   Pareto frontier line drawn.

Each figure is saved as both PNG (150 dpi) and SVG.

Real-world analogy:
    A medical journal's "results" section: survival curves (reward),
    adverse event rates (violations), treatment failure frequencies
    (deadlocks), and efficacy-vs-safety tradeoff (Pareto).
"""

import os
import statistics

from ..experiments.metrics import ExperimentReport
from .analysis import _bootstrap_ci

_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
_MARKERS = ["o", "s", "D", "^", "v"]


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def _ci_to_error(values: list[float], n_resamples: int = 100) -> tuple[list[float], list[float]]:
    """Convert bootstrap CI bounds to matplotlib-compatible asymmetric error.

    For a bar plot, matplotlib ``yerr`` expects ``(2, N)`` or ``(N,)``.
    This helper returns ``(lower_errors, upper_errors)`` where each element
    is the distance from the mean to the respective CI bound.

    Args:
        values: Observed values.
        n_resamples: Bootstrap resamples (default 100 — sufficient for
            visualization; increase for publication-grade precision).

    Returns:
        ``(lower_errors, upper_errors)`` — each a list of length 1
        (single bar group) so that the caller can build the ``(2, N)`` array.
    """
    if not values:
        return ([0.0], [0.0])
    mean = statistics.mean(values)
    lo, hi = _bootstrap_ci(values, n_resamples=n_resamples)
    return ([mean - lo], [hi - mean])


def plot_reward_curves(reports: list[ExperimentReport], output_dir: str = "results/figures"):
    """Plot mean cumulative reward curves with 95% bootstrap CI shaded bands.

    Creates a 2×2 subplot panel with one scenario per subplot.
    Each subplot shows all strategies as separate coloured lines.
    Confidence bands derived from :func:`_bootstrap_ci` instead of
    parametric normal approximation.

    The curve is each step record's ``cumulative_reward``, not the
    per-step ``reward`` that now sits beside it. Reading the wrong key
    would turn the panel from a running total into a scatter of
    single-step payoffs under an axis labelled "Cumulative Reward"
    (#304).

    Args:
        reports: List of experiment reports.
        output_dir: Directory for output files (default ``results/figures``).

    Returns:
        The :class:`matplotlib.figure.Figure` object.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _ensure_dir(f"{output_dir}/reward_curves.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("Reward Curves Over Time", fontsize=14, fontweight="bold")

    for idx, scenario in enumerate(scenarios):
        ax = axes[idx // 2][idx % 2]
        ax.set_title(scenario)

        for sidx, strategy in enumerate(strategies):
            relevant = [
                r
                for r in reports
                if r.metadata.get("scenario") == scenario and r.metadata.get("strategy") == strategy
            ]
            if not relevant:
                continue

            all_curves = []
            for r in relevant:
                steps = r.metadata.get("step_records", [])
                curve = [s.get("cumulative_reward", 0) for s in steps]
                if curve:
                    all_curves.append(curve)

            if not all_curves:
                continue

            min_len = min(len(c) for c in all_curves)
            aligned = [c[:min_len] for c in all_curves]

            means = [statistics.mean([c[i] for c in aligned]) for i in range(min_len)]
            cis = []
            for i in range(min_len):
                step_vals = [c[i] for c in aligned]
                lo, hi = _bootstrap_ci(step_vals, n_resamples=100)
                cis.append((lo, hi))

            x = list(range(min_len))
            color = _COLORS[sidx % len(_COLORS)]
            ax.plot(x, means, label=strategy, color=color, linewidth=1.5)
            ax.fill_between(
                x,
                [c[0] for c in cis],
                [c[1] for c in cis],
                alpha=0.15,
                color=color,
            )

        ax.set_xlabel("Step")
        ax.set_ylabel("Cumulative Reward")
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/reward_curves.png", dpi=150)
    plt.savefig(f"{output_dir}/reward_curves.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/reward_curves.png")
    return fig


def plot_violation_rates(reports: list[ExperimentReport], output_dir: str = "results/figures"):
    """Plot grouped bar chart of constraint violation rates per scenario.

    Each strategy is a different coloured bar within each scenario group.
    Error bars are 95% bootstrap CIs (asymmetric).

    A scenario-strategy pair with no reports gets no bar at all, rather than
    a bar of height zero: an arm that was never run has no violation rate,
    and drawing it at zero would publish the most favourable possible number
    for a measurement that does not exist.

    Args:
        reports: List of experiment reports.
        output_dir: Directory for output files.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _ensure_dir(f"{output_dir}/violation_rates.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))

    x = np.arange(len(scenarios))
    width = 0.8 / max(len(strategies), 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Constraint Violation Rates by Scenario", fontsize=14, fontweight="bold")

    for sidx, strategy in enumerate(strategies):
        positions = []
        means = []
        lower_err = []
        upper_err = []
        for xpos, scenario in zip(x, scenarios):
            relevant = [
                r
                for r in reports
                if r.metadata.get("scenario") == scenario and r.metadata.get("strategy") == strategy
            ]
            if not relevant:
                continue
            vals = [r.constraint_violations / max(r.total_steps, 1) for r in relevant]
            mean = statistics.mean(vals)
            lo, hi = _bootstrap_ci(vals)
            positions.append(xpos)
            means.append(mean)
            lower_err.append(mean - lo)
            upper_err.append(hi - mean)

        offset = (sidx - len(strategies) / 2 + 0.5) * width
        ax.bar(
            np.array(positions, dtype=float) + offset,
            means,
            width,
            label=strategy,
            color=_COLORS[sidx % len(_COLORS)],
            yerr=np.array([lower_err, upper_err]),
            capsize=3,
        )

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
    return fig


def plot_deadlock_frequency(reports: list[ExperimentReport], output_dir: str = "results/figures"):
    """Plot grouped bar chart of deadlock rates per scenario.

    Error bars are 95% bootstrap CIs (asymmetric).

    As in :func:`plot_violation_rates`, a scenario-strategy pair with no
    reports gets no bar rather than a bar of height zero.

    Args:
        reports: List of experiment reports.
        output_dir: Directory for output files.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _ensure_dir(f"{output_dir}/deadlock_frequency.png")

    scenarios = sorted(set(r.metadata.get("scenario", "unknown") for r in reports))
    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))

    x = np.arange(len(scenarios))
    width = 0.8 / max(len(strategies), 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Deadlock Frequency by Scenario", fontsize=14, fontweight="bold")

    for sidx, strategy in enumerate(strategies):
        positions = []
        means = []
        lower_err = []
        upper_err = []
        for xpos, scenario in zip(x, scenarios):
            relevant = [
                r
                for r in reports
                if r.metadata.get("scenario") == scenario and r.metadata.get("strategy") == strategy
            ]
            if not relevant:
                continue
            vals = [r.deadlock_rate for r in relevant]
            mean = statistics.mean(vals)
            lo, hi = _bootstrap_ci(vals)
            positions.append(xpos)
            means.append(mean)
            lower_err.append(mean - lo)
            upper_err.append(hi - mean)

        offset = (sidx - len(strategies) / 2 + 0.5) * width
        ax.bar(
            np.array(positions, dtype=float) + offset,
            means,
            width,
            label=strategy,
            color=_COLORS[sidx % len(_COLORS)],
            yerr=np.array([lower_err, upper_err]),
            capsize=3,
        )

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
    return fig


def plot_pareto_frontier(reports: list[ExperimentReport], output_dir: str = "results/figures"):
    """Plot Pareto frontier of total reward vs. constraint violations.

    Each point is a single run.  The upper-left region is the Pareto-optimal
    frontier (high reward, few violations).  A step line connecting the
    non-dominated points is overlaid.

    Args:
        reports: List of experiment reports.
        output_dir: Directory for output files.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _ensure_dir(f"{output_dir}/pareto_frontier.png")

    strategies = sorted(set(r.metadata.get("strategy", "unknown") for r in reports))

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Pareto Frontier: Reward vs Safety", fontsize=14, fontweight="bold")

    all_points = []
    for sidx, strategy in enumerate(strategies):
        relevant = [r for r in reports if r.metadata.get("strategy") == strategy]
        if not relevant:
            continue

        rewards = [r.total_reward for r in relevant]
        violations = [r.constraint_violations for r in relevant]
        points = list(zip(violations, rewards))
        all_points.extend(points)

        ax.scatter(
            violations,
            rewards,
            label=strategy,
            color=_COLORS[sidx % len(_COLORS)],
            marker=_MARKERS[sidx % len(_MARKERS)],
            alpha=0.6,
            s=40,
        )

    if all_points:
        n = len(all_points)
        is_dominated = [False] * n
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                vi, ri = all_points[i]
                vj, rj = all_points[j]
                if vj <= vi and rj >= ri and (vj < vi or rj > ri):
                    is_dominated[i] = True
                    break

        frontier = [all_points[i] for i in range(n) if not is_dominated[i]]
        frontier.sort(key=lambda p: (p[0], -p[1]))

        if frontier:
            f_v = [p[0] for p in frontier]
            f_r = [p[1] for p in frontier]
            ax.step(
                f_v,
                f_r,
                where="post",
                color="black",
                linewidth=1.5,
                linestyle="--",
                label="Pareto frontier",
            )

    ax.set_xlabel("Total Constraint Violations")
    ax.set_ylabel("Total Reward")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/pareto_frontier.png", dpi=150)
    plt.savefig(f"{output_dir}/pareto_frontier.svg", format="svg")
    plt.close()
    print(f"  -> {output_dir}/pareto_frontier.png")
    return fig


def generate_all_figures(
    reports: list[ExperimentReport], output_dir: str = "results/figures"
) -> dict:
    """Generate all four publication-ready figures.

    Args:
        reports: List of experiment reports.
        output_dir: Directory for output files.

    Returns:
        Dict mapping figure names to :class:`matplotlib.figure.Figure` objects.
    """
    print("Generating figures...")
    figs = {
        "reward_curves": plot_reward_curves(reports, output_dir),
        "violation_rates": plot_violation_rates(reports, output_dir),
        "deadlock_frequency": plot_deadlock_frequency(reports, output_dir),
        "pareto_frontier": plot_pareto_frontier(reports, output_dir),
    }
    print(f"All figures saved to {output_dir}/")
    return figs


if __name__ == "__main__":
    from .run_all import (
        run_deadlock_experiments,
        run_drift_experiments,
        run_gridworld_experiments,
        run_temptation_experiments,
    )

    reports = []
    for runner, scenario in [
        (run_gridworld_experiments, "GridWorld"),
        (run_temptation_experiments, "TemptationBank"),
        (run_drift_experiments, "DriftLab"),
        (run_deadlock_experiments, "DeadlockMaze"),
    ]:
        reps = runner(steps=50, seeds=3, strategies=["governance", "monolithic_rl", "random"])
        for r in reps:
            r.metadata["scenario"] = scenario
        reports.extend(reps)

    generate_all_figures(reports)
