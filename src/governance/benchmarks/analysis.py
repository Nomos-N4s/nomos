"""
Statistical analysis pipeline for benchmark results.

Computes per-strategy-scenario aggregates with bootstrap confidence
intervals, Cohen's :math:`d` effect sizes comparing governance against
each baseline, detects reward-hacking episodes, and exports to JSON/CSV.

Real-world analogy:
    A medical trial analysis: split patients by treatment group (strategy),
    compute mean outcomes (reward), statistical significance (effect sizes),
    and flag adverse events (reward hacking).
"""

import csv
import json
import math
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass

from ..experiments.metrics import ExperimentReport


def _bootstrap_ci(
    values: list[float], n_resamples: int = 10000, ci: float = 0.95
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for a list of values.

    Args:
        values: The observed values.
        n_resamples: Number of bootstrap resamples (default 10000).
        ci: Confidence level (default 0.95).

    Returns:
        ``(lower_bound, upper_bound)``.
    """
    if len(values) < 2:
        return (values[0] if values else 0.0, values[0] if values else 0.0)
    import random as _random

    rng = _random.Random(42)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(statistics.mean(sample))
    means.sort()
    lower_idx = int(n_resamples * (1 - ci) / 2)
    upper_idx = int(n_resamples * (1 + ci) / 2)
    return (means[lower_idx], means[upper_idx - 1])


def _cohens_d(control: list[float], treatment: list[float]) -> float:
    """Compute Cohen's d effect size between two groups.

    Positive values mean the control (governance) outperforms treatment.

    Args:
        control: Governance rewards.
        treatment: Baseline rewards.

    Returns:
        Cohen's d value. Conventional thresholds:
        |d| < 0.2 negligible, < 0.5 small, < 0.8 medium, >= 0.8 large.
    """
    if len(control) < 2 or len(treatment) < 2:
        return 0.0
    m1 = statistics.mean(control)
    m2 = statistics.mean(treatment)
    v1 = statistics.variance(control)
    v2 = statistics.variance(treatment)
    n1, n2 = len(control), len(treatment)
    pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled == 0:
        return 0.0
    return (m1 - m2) / pooled


def _mannwhitney_u(x: list[float], y: list[float]) -> tuple[float, float]:
    """Compute Mann-Whitney U test and two-tailed p-value (normal approx).

    Uses the normal approximation with tie correction, valid when both
    sample sizes are >= 8.

    Args:
        x: First group of observed values.
        y: Second group of observed values.

    Returns:
        ``(U_statistic, p_value)`` -- U is the smaller of U1 and U2.
        Returns ``(0.0, 1.0)`` if either group has fewer than 2 elements.
    """
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return (0.0, 1.0)

    combined = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    n = n1 + n2
    ranks = [0.0] * n
    tie_adjustment = 0.0
    i = 0
    while i < n:
        j = i
        while j < n and combined[j][0] == combined[i][0]:
            j += 1
        tie_count = j - i
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        if tie_count > 1:
            tie_adjustment += tie_count**3 - tie_count
        i = j

    r1 = sum(ranks[k] for k in range(n) if combined[k][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    mean_u = n1 * n2 / 2.0
    variance = (n1 * n2 / 12.0) * ((n + 1) - tie_adjustment / (n * (n - 1)))
    if variance <= 0:
        return (round(u, 2), 1.0)

    z = (u - mean_u) / math.sqrt(variance)
    p = math.erfc(abs(z) / math.sqrt(2.0))
    p = max(0.0, min(1.0, p))
    return (round(u, 2), round(p, 4))


def _bonferroni_correct(p_values: list[float], alpha: float = 0.05) -> list[dict]:
    """Apply Bonferroni correction for multiple comparisons.

    Args:
        p_values: Raw p-values (one per comparison).
        alpha: Family-wise error rate (default 0.05).

    Returns:
        List of dicts with keys ``raw_p``, ``corrected_p``, ``significant``.
    """
    m = len(p_values)
    if m == 0:
        return []
    results = []
    for raw_p in p_values:
        corrected = min(raw_p * m, 1.0)
        results.append(
            {
                "raw_p": raw_p,
                "corrected_p": round(corrected, 4),
                "significant": corrected < alpha,
            }
        )
    return results


def _detect_reward_hacking(step_records: list[dict], window: int = 10) -> list[dict]:
    """Detect reward-hacking episodes from step-level records.

    A reward-hacking episode is defined as a step where a violation occurs
    AND the mean reward in the trailing 5 steps is 50% higher than the
    preceding window.

    Args:
        step_records: List of per-step dicts with ``reward`` and
            ``violations`` keys.
        window: Number of steps to look back for the baseline comparison
            window (default 10).

    Returns:
        List of episode dicts with ``step``, ``reward_spike``, and
        ``violation_count``.
    """
    episodes = []
    for i in range(len(step_records)):
        if step_records[i].get("violations", 0) > 0:
            window_start = max(0, i - window)
            window_rewards = [r.get("reward", 0) for r in step_records[window_start : i + 1]]
            if len(window_rewards) >= 2:
                recent = window_rewards[-min(5, len(window_rewards)) :]
                earlier = window_rewards[: -min(5, len(window_rewards))]
                if earlier and statistics.mean(recent) > statistics.mean(earlier) * 1.5:
                    episodes.append(
                        {
                            "step": i,
                            "reward_spike": round(
                                statistics.mean(recent) - statistics.mean(earlier), 2
                            ),
                            "violation_count": step_records[i].get("violations", 0),
                        }
                    )
    return episodes


@dataclass
class StrategyAggregate:
    """Aggregated statistics for a single strategy-scenario pair.

    Attributes:
        strategy: Strategy name (e.g. ``"governance"``).
        scenario: Scenario name (e.g. ``"GridWorld"``).
        num_seeds: Number of random seeds in the aggregate.
        mean_reward: Mean total reward across seeds.
        std_reward: Standard deviation of total reward.
        mean_deadlocks: Mean deadlock count across seeds.
        mean_violations: Mean constraint violation count.
        ci_lower: Bootstrap 95% CI lower bound.
        ci_upper: Bootstrap 95% CI upper bound.
    """

    strategy: str
    scenario: str
    num_seeds: int
    mean_reward: float
    std_reward: float
    mean_deadlocks: float
    mean_violations: float
    ci_lower: float
    ci_upper: float


def aggregate_reports(reports: list[ExperimentReport]) -> list[StrategyAggregate]:
    """Group reports by strategy+scenario and compute aggregates.

    Args:
        reports: Flattened list of all experiment reports.

    Returns:
        List of :class:`StrategyAggregate` instances.
    """
    groups = defaultdict(list)
    for r in reports:
        key = (r.metadata.get("strategy", "unknown"), r.metadata.get("scenario", "unknown"))
        groups[key].append(r)

    results = []
    for (strategy, scenario), reps in sorted(groups.items()):
        rewards = [r.total_reward for r in reps]
        ci_l, ci_u = _bootstrap_ci(rewards)
        results.append(
            StrategyAggregate(
                strategy=strategy,
                scenario=scenario,
                num_seeds=len(reps),
                mean_reward=statistics.mean(rewards),
                std_reward=statistics.stdev(rewards) if len(rewards) > 1 else 0.0,
                mean_deadlocks=statistics.mean([r.deadlock_count for r in reps]),
                mean_violations=statistics.mean([r.constraint_violations for r in reps]),
                ci_lower=ci_l,
                ci_upper=ci_u,
            )
        )
    return results


def compute_effect_sizes(
    aggregates: list[StrategyAggregate],
    reports: list[ExperimentReport],
    alpha: float = 0.05,
) -> list[dict]:
    """Compute Cohen's d and Mann-Whitney U with Bonferroni correction.

    For each scenario, governance rewards are compared against every
    baseline using Cohen's d (parametric effect size) and Mann-Whitney U
    (non-parametric test). Raw p-values are Bonferroni-corrected across
    all comparisons within the call.

    Args:
        aggregates: Aggregates (used to determine which scenarios exist).
        reports: Full report list (used to access raw rewards per group).
        alpha: Family-wise error rate for Bonferroni correction (default 0.05).

    Returns:
        List of dicts with keys ``scenario``, ``governance_vs``, ``cohens_d``,
        ``mannwhitney_u``, ``p_value_raw``, ``p_value_corrected``,
        ``significant``, ``n_governance``, ``n_baseline``, ``interpretation``.
    """
    groups = defaultdict(list)
    for r in reports:
        key = (r.metadata.get("strategy", "unknown"), r.metadata.get("scenario", "unknown"))
        groups[key].append(r.total_reward)

    effect_sizes = []
    scenarios = set(s.scenario for s in aggregates)
    governance_key = "governance"
    baselines = ["monolithic_rl", "random", "static_masking", "veto_only"]

    raw_p_values = []
    for scenario in sorted(scenarios):
        control_rewards = groups.get((governance_key, scenario), [])
        for bl in baselines:
            treatment_rewards = groups.get((bl, scenario), [])
            d = _cohens_d(control_rewards, treatment_rewards)
            u_stat, p_raw = _mannwhitney_u(control_rewards, treatment_rewards)
            raw_p_values.append(p_raw)
            effect_sizes.append(
                {
                    "scenario": scenario,
                    "governance_vs": bl,
                    "cohens_d": round(d, 3),
                    "mannwhitney_u": u_stat,
                    "p_value_raw": p_raw,
                    "n_governance": len(control_rewards),
                    "n_baseline": len(treatment_rewards),
                    "interpretation": (
                        "large"
                        if abs(d) > 0.8
                        else "medium"
                        if abs(d) > 0.5
                        else "small"
                        if abs(d) > 0.2
                        else "negligible"
                    ),
                }
            )

    corrections = _bonferroni_correct(raw_p_values, alpha)
    for es, corr in zip(effect_sizes, corrections):
        es["p_value_corrected"] = corr["corrected_p"]
        es["significant"] = corr["significant"]

    return effect_sizes


def detect_hacking_episodes(reports: list[ExperimentReport]) -> list[dict]:
    """Scan all reports for reward-hacking episodes.

    Each episode is tagged with its strategy, scenario, and seed for
    traceability.

    Args:
        reports: List of all experiment reports.

    Returns:
        List of episode dicts.
    """
    all_episodes = []
    for r in reports:
        step_records = r.metadata.get("step_records", [])
        episodes = _detect_reward_hacking(step_records)
        for ep in episodes:
            ep["strategy"] = r.metadata.get("strategy", "unknown")
            ep["scenario"] = r.metadata.get("scenario", "unknown")
            ep["seed"] = r.metadata.get("seed", 0)
            all_episodes.append(ep)
    return all_episodes


def export_summary_csv(aggregates: list[StrategyAggregate], path: str):
    """Export aggregate statistics to a CSV file.

    Args:
        aggregates: The aggregates to export.
        path: File path for the CSV output.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "strategy",
                "scenario",
                "num_seeds",
                "mean_reward",
                "std_reward",
                "mean_deadlocks",
                "mean_violations",
                "ci_lower",
                "ci_upper",
            ]
        )
        for a in aggregates:
            w.writerow(
                [
                    a.strategy,
                    a.scenario,
                    a.num_seeds,
                    round(a.mean_reward, 2),
                    round(a.std_reward, 2),
                    round(a.mean_deadlocks, 2),
                    round(a.mean_violations, 2),
                    round(a.ci_lower, 2),
                    round(a.ci_upper, 2),
                ]
            )


def export_results_json(
    reports: list[ExperimentReport],
    aggregates: list[StrategyAggregate],
    effect_sizes: list[dict],
    hacking_episodes: list[dict],
    path: str,
):
    """Export all analysis results to a single JSON file.

    Args:
        reports: Full report list.
        aggregates: Aggregates.
        effect_sizes: Effect size comparisons.
        hacking_episodes: Detected episodes.
        path: File path for JSON output.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {
        "aggregates": [
            {
                "strategy": a.strategy,
                "scenario": a.scenario,
                "num_seeds": a.num_seeds,
                "mean_reward": a.mean_reward,
                "std_reward": a.std_reward,
                "mean_deadlocks": a.mean_deadlocks,
                "mean_violations": a.mean_violations,
                "ci_lower": a.ci_lower,
                "ci_upper": a.ci_upper,
            }
            for a in aggregates
        ],
        "effect_sizes": effect_sizes,
        "reward_hacking_episodes": hacking_episodes[:50],
        "num_reports": len(reports),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_analysis(reports: list[ExperimentReport], output_dir: str = "results") -> dict:
    """Run the full analysis pipeline: aggregate, effect sizes, detect, export.

    Args:
        reports: All experiment reports.
        output_dir: Directory for output files (default ``"results"``).

    Returns:
        Dict with keys ``aggregates``, ``effect_sizes``, ``hacking_episodes``,
        ``summary_csv``, ``results_json``.
    """
    os.makedirs(output_dir, exist_ok=True)

    aggregates = aggregate_reports(reports)
    effect_sizes = compute_effect_sizes(aggregates, reports)
    hacking_episodes = detect_hacking_episodes(reports)

    summary_csv = os.path.join(output_dir, "benchmark_summary.csv")
    results_json = os.path.join(output_dir, "benchmark_results.json")

    export_summary_csv(aggregates, summary_csv)
    export_results_json(reports, aggregates, effect_sizes, hacking_episodes, results_json)

    return {
        "aggregates": aggregates,
        "effect_sizes": effect_sizes,
        "hacking_episodes": hacking_episodes,
        "summary_csv": summary_csv,
        "results_json": results_json,
    }


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

    result = run_analysis(reports)
    print(f"Summary: {result['summary_csv']}")
    print(f"Results: {result['results_json']}")
    print(f"Effect sizes: {len(result['effect_sizes'])}")
    print(f"Hacking episodes: {len(result['hacking_episodes'])}")
