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
from typing import Any, Dict, List, Optional, Tuple

from ..experiments.metrics import ExperimentReport


def _bootstrap_ci(values: List[float], n_resamples: int = 10000,
                  ci: float = 0.95) -> Tuple[float, float]:
    """Compute bootstrap confidence interval for a list of values.

    Args:
        values: The observed values.
        n_resamples: Number of bootstrap resamples (default 10000).
        ci: Confidence level (default 0.95).

    Returns:
        ``(lower_bound, upper_bound)``.
    """
    if len(values) < 2:
        return (values[0] if values else 0.0,
                values[0] if values else 0.0)
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


def _cohens_d(control: List[float], treatment: List[float]) -> float:
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


def _detect_reward_hacking(step_records: List[Dict],
                           window: int = 10) -> List[Dict]:
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
            window_rewards = [r.get("reward", 0) for r in
                              step_records[window_start:i + 1]]
            if len(window_rewards) >= 2:
                recent = window_rewards[-min(5, len(window_rewards)):]
                earlier = window_rewards[:-min(5, len(window_rewards))]
                if earlier and statistics.mean(recent) > statistics.mean(earlier) * 1.5:
                    episodes.append({
                        "step": i,
                        "reward_spike": round(statistics.mean(recent) - statistics.mean(earlier), 2),
                        "violation_count": step_records[i].get("violations", 0),
                    })
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


def aggregate_reports(reports: List[ExperimentReport]) -> List[StrategyAggregate]:
    """Group reports by strategy+scenario and compute aggregates.

    Args:
        reports: Flattened list of all experiment reports.

    Returns:
        List of :class:`StrategyAggregate` instances.
    """
    groups = defaultdict(list)
    for r in reports:
        key = (r.metadata.get("strategy", "unknown"),
               r.metadata.get("scenario", "unknown"))
        groups[key].append(r)

    results = []
    for (strategy, scenario), reps in sorted(groups.items()):
        rewards = [r.total_reward for r in reps]
        ci_l, ci_u = _bootstrap_ci(rewards)
        results.append(StrategyAggregate(
            strategy=strategy,
            scenario=scenario,
            num_seeds=len(reps),
            mean_reward=statistics.mean(rewards),
            std_reward=statistics.stdev(rewards) if len(rewards) > 1 else 0.0,
            mean_deadlocks=statistics.mean([r.deadlock_count for r in reps]),
            mean_violations=statistics.mean([r.constraint_violations for r in reps]),
            ci_lower=ci_l,
            ci_upper=ci_u,
        ))
    return results


def compute_effect_sizes(
    aggregates: List[StrategyAggregate],
    reports: List[ExperimentReport],
) -> List[Dict]:
    """Compute Cohen's d for each scenario comparing governance vs baselines.

    Args:
        aggregates: Aggregates (used to determine which scenarios exist).
        reports: Full report list (used to access raw rewards per group).

    Returns:
        List of dicts with keys ``scenario``, ``governance_vs`` (baseline name),
        ``cohens_d``, ``n_governance``, ``n_baseline``, ``interpretation``.
    """
    groups = defaultdict(list)
    for r in reports:
        key = (r.metadata.get("strategy", "unknown"),
               r.metadata.get("scenario", "unknown"))
        groups[key].append(r.total_reward)

    effect_sizes = []
    scenarios = set(s.scenario for s in aggregates)
    governance_key = "governance"
    baselines = ["monolithic_rl", "random", "static_masking", "veto_only"]

    for scenario in sorted(scenarios):
        control_rewards = groups.get((governance_key, scenario), [])
        for bl in baselines:
            treatment_rewards = groups.get((bl, scenario), [])
            d = _cohens_d(control_rewards, treatment_rewards)
            effect_sizes.append({
                "scenario": scenario,
                "governance_vs": bl,
                "cohens_d": round(d, 3),
                "n_governance": len(control_rewards),
                "n_baseline": len(treatment_rewards),
                "interpretation": (
                    "large" if abs(d) > 0.8 else
                    "medium" if abs(d) > 0.5 else
                    "small" if abs(d) > 0.2 else
                    "negligible"
                ),
            })
    return effect_sizes


def detect_hacking_episodes(reports: List[ExperimentReport]) -> List[Dict]:
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


def export_summary_csv(aggregates: List[StrategyAggregate], path: str):
    """Export aggregate statistics to a CSV file.

    Args:
        aggregates: The aggregates to export.
        path: File path for the CSV output.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "scenario", "num_seeds",
                     "mean_reward", "std_reward",
                     "mean_deadlocks", "mean_violations",
                     "ci_lower", "ci_upper"])
        for a in aggregates:
            w.writerow([a.strategy, a.scenario, a.num_seeds,
                        round(a.mean_reward, 2), round(a.std_reward, 2),
                        round(a.mean_deadlocks, 2), round(a.mean_violations, 2),
                        round(a.ci_lower, 2), round(a.ci_upper, 2)])


def export_results_json(reports: List[ExperimentReport],
                         aggregates: List[StrategyAggregate],
                         effect_sizes: List[Dict],
                         hacking_episodes: List[Dict],
                         path: str):
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


def run_analysis(reports: List[ExperimentReport],
                 output_dir: str = "results") -> Dict:
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
    export_results_json(reports, aggregates, effect_sizes, hacking_episodes,
                        results_json)

    return {
        "aggregates": aggregates,
        "effect_sizes": effect_sizes,
        "hacking_episodes": hacking_episodes,
        "summary_csv": summary_csv,
        "results_json": results_json,
    }


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

    result = run_analysis(reports)
    print(f"Summary: {result['summary_csv']}")
    print(f"Results: {result['results_json']}")
    print(f"Effect sizes: {len(result['effect_sizes'])}")
    print(f"Hacking episodes: {len(result['hacking_episodes'])}")