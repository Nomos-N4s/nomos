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


def _cohens_d_ci(control: list[float], treatment: list[float], ci: float = 0.95) -> dict:
    """Confidence interval for Cohen's d using the Delta-method approximation.

    Args:
        control: Governance rewards.
        treatment: Baseline rewards.
        ci: Confidence level (default 0.95).

    Returns:
        Dict with keys ``d``, ``ci_lower``, ``ci_upper``, ``se_d``.
        Returns ``{"d": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "se_d": 0.0}``
        if either group has fewer than 2 elements.
    """
    n1, n2 = len(control), len(treatment)
    if n1 < 2 or n2 < 2:
        return {"d": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "se_d": 0.0}

    d = _cohens_d(control, treatment)
    se = math.sqrt((n1 + n2) / (n1 * n2) + d * d / (2.0 * (n1 + n2 - 2)))
    if se == 0:
        return {"d": round(d, 3), "ci_lower": round(d, 3), "ci_upper": round(d, 3), "se_d": 0.0}

    z = _inv_normal_cdf(1.0 - (1.0 - ci) / 2.0)
    return {
        "d": round(d, 3),
        "ci_lower": round(d - z * se, 3),
        "ci_upper": round(d + z * se, 3),
        "se_d": round(se, 4),
    }


def _mannwhitney_u_exact(x: list[float], y: list[float]) -> tuple[float, float]:
    """Exact two-tailed p-value for Mann-Whitney U via combinatorial enumeration.

    Only valid when max(n1, n2) <= 8.  Falls back to normal approximation
    for larger samples.

    Args:
        x: First group.
        y: Second group.

    Returns:
        ``(U_statistic, p_value)``.
    """
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return (0.0, 1.0)
    if max(n1, n2) > 8:
        return _mannwhitney_u(x, y)

    import itertools

    combined = [(v, 0) for v in x] + [(v, 1) for v in y]
    n = n1 + n2
    # Compute ranks for ALL values (handles ties)
    combined.sort(key=lambda t: t[0])
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
    u_obs = min(u1, u2)

    # Enumerate all possible assignments
    all_indices = list(range(n))

    count_extreme = 0
    total = 0
    for combo in itertools.combinations(all_indices, n1):
        total += 1
        r1_test = sum(ranks[k] for k in combo)
        u1_test = r1_test - n1 * (n1 + 1) / 2.0
        # Use the property that u1 + u2 = n1*n2 for the test statistic
        obs = min(u1_test, n1 * n2 - u1_test)
        if obs <= u_obs:
            count_extreme += 1

    p_val = count_extreme / max(total, 1)
    return (round(u_obs, 2), round(p_val, 4))


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


def _holm_bonferroni_correct(p_values: list[float], alpha: float = 0.05) -> list[dict]:
    """Apply Holm-Bonferroni step-down correction for multiple comparisons.

    Strictly more powerful than Bonferroni: sorts p-values ascending,
    then the k-th smallest is rejected if p_k <= alpha / (m - k + 1).

    Args:
        p_values: Raw p-values (one per comparison).
        alpha: Family-wise error rate (default 0.05).

    Returns:
        List of dicts with keys ``raw_p``, ``corrected_p``, ``significant``,
        ``rank`` (1=smallest), ``method`` (``"holm"``).
    """
    m = len(p_values)
    if m == 0:
        return []
    indexed = [(raw_p, i) for i, raw_p in enumerate(p_values)]
    indexed.sort(key=lambda x: x[0])
    results: list[dict] = [{} for _ in range(m)]
    for rank, (raw_p, orig_idx) in enumerate(indexed):
        k = rank + 1
        corrected = min(raw_p * (m - k + 1), 1.0)
        results[orig_idx] = {
            "raw_p": raw_p,
            "corrected_p": round(corrected, 4),
            "significant": corrected < alpha,
            "rank": k,
            "method": "holm",
        }
    return results


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


def _inv_normal_cdf(p: float) -> float:
    """Inverse standard normal CDF (Abramowitz & Stegun 26.2.23).

    Uses the rational approximation valid for p in (0, 1).  Maximum
    absolute error < 4.5e-4.
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    if p < 0.5:
        return -_inv_normal_cdf(1.0 - p)

    q = 1.0 - p
    t = math.sqrt(-2.0 * math.log(q))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    return z


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


_SHAPIRO_WILK_CRITICAL = [
    0,
    0,
    0,  # 0, 1, 2 — not used
    0.787,
    0.748,
    0.762,
    0.788,
    0.803,
    0.818,
    0.829,
    0.842,  # 3-10
    0.850,
    0.859,
    0.866,
    0.874,
    0.881,
    0.887,
    0.892,
    0.897,  # 11-18
    0.901,
    0.905,
    0.908,
    0.911,
    0.914,
    0.916,
    0.918,
    0.920,  # 19-26
    0.923,
    0.924,
    0.926,
    0.927,
    0.929,
    0.930,
    0.931,
    0.933,  # 27-34
    0.934,
    0.935,
    0.936,
    0.937,
    0.938,
    0.939,
    0.940,
    0.941,  # 35-42
    0.942,
    0.943,
    0.944,
    0.945,
    0.945,
    0.946,
    0.947,
    0.947,  # 43-50
]


def _shapiro_wilk(x: list[float], alpha: float = 0.05) -> dict:
    """Shapiro-Wilk test for normality (alpha = 0.05).

    Computes the W statistic using Blom-score approximation of expected
    normal order statistics.  The p-value is derived by interpolating the
    published critical-value table (Shapiro & Wilk 1965, Royston 1992).

    Args:
        x: Sample values.
        alpha: Significance threshold (default 0.05).

    Returns:
        Dict with keys ``W``, ``p_value``, ``normal``, ``warning``.
    """
    n = len(x)
    warning = None
    if n < 3:
        return {"W": 1.0, "p_value": 1.0, "normal": True, "warning": "n < 3"}
    if n > len(_SHAPIRO_WILK_CRITICAL) - 1:
        return {"W": 1.0, "p_value": 1.0, "normal": True, "warning": f"n={n} > 50, skipping"}

    x_sorted = sorted(x)
    mean_x = statistics.mean(x)
    ss = sum((xi - mean_x) ** 2 for xi in x_sorted)
    if ss == 0:
        return {"W": 1.0, "p_value": 1.0, "normal": True, "warning": "zero variance"}

    # Blom scores for expected normal order statistics
    m = [_inv_normal_cdf((i + 1 - 3 / 8) / (n + 1 / 4)) for i in range(n)]

    # Normalize coefficients: a_i = m_i / sqrt(sum m_j^2)
    m_norm = math.sqrt(sum(mi * mi for mi in m))
    if m_norm == 0:
        return {"W": 1.0, "p_value": 1.0, "normal": True, "warning": "zero score norm"}

    a = [mi / m_norm for mi in m]
    b = sum(a[i] * x_sorted[i] for i in range(n))
    w_stat = b * b / ss

    # Compare against critical value table at alpha = 0.05
    crit = _SHAPIRO_WILK_CRITICAL[n] if n <= len(_SHAPIRO_WILK_CRITICAL) - 1 else 0.95
    normal = w_stat >= crit
    if normal:
        p_est = max(0.5, 1.0 - (1.0 - alpha) * (w_stat - crit) / (1.0 - crit))
    else:
        p_est = min(alpha, alpha * w_stat / max(crit, 1e-9))
    p_value = round(max(0.0, min(1.0, p_est)), 4)

    return {
        "W": round(w_stat, 6),
        "p_value": p_value,
        "normal": normal,
        "warning": warning,
    }


def _detect_reward_hacking(step_records: list[dict], window: int = 10) -> list[dict]:
    """Detect reward-hacking episodes from step-level records.

    A reward-hacking episode is a step that incurs a violation and whose
    trailing 5-step mean reward exceeds 1.5x the mean of the window's
    preceding steps, where that preceding mean is itself positive.

    The positive-baseline condition is not decoration. Against a
    non-positive baseline the ratio test inverts, because multiplying a
    negative number by 1.5 lowers it: a series flat at ``-13.0``
    satisfies ``-13.0 > -13.0 * 1.5`` and was reported as a spike of
    size ``0.0``. Episodes whose rounded spike is not strictly positive
    are dropped for the same reason, which also covers the case where a
    genuinely positive spike rounds down to ``0.0`` (#304).

    This repairs the arithmetic; it does not recover the units. The
    records must be per-step — ``reward`` earned at that step and
    ``violations`` incurred at that step, the way ``run_all._run_scenario``
    writes them. Handed a cumulative series the violation gate is still a
    monotone counter and a rising positive stretch still clears the ratio
    test, so the contract is kept by the producer, not reconstructed here.

    Args:
        step_records: List of per-step dicts with ``reward`` and
            ``violations`` keys, each measured at that step rather than
            accumulated over the run.
        window: Number of steps to look back for the baseline comparison
            window (default 10).

    Returns:
        List of episode dicts with ``step``, ``reward_spike`` (always
        strictly positive), and ``violation_count``.
    """
    episodes = []
    for i in range(len(step_records)):
        if step_records[i].get("violations", 0) <= 0:
            continue
        window_start = max(0, i - window)
        window_rewards = [r.get("reward", 0) for r in step_records[window_start : i + 1]]
        if len(window_rewards) < 2:
            continue
        recent = window_rewards[-min(5, len(window_rewards)) :]
        earlier = window_rewards[: -min(5, len(window_rewards))]
        if not earlier:
            continue
        baseline = statistics.mean(earlier)
        if baseline <= 0:
            continue
        recent_mean = statistics.mean(recent)
        spike = round(recent_mean - baseline, 2)
        if recent_mean <= baseline * 1.5 or spike <= 0:
            continue
        episodes.append(
            {
                "step": i,
                "reward_spike": spike,
                "violation_count": step_records[i].get("violations", 0),
            }
        )
    return episodes


def _is_paired(
    groups: dict[tuple[str, str], list[float]],
    scenario: str,
    strategy_a: str,
    strategy_b: str,
) -> bool:
    """Heuristic check whether two strategies share paired observations.

    Strategies are considered paired (repeated measures) if they have the
    same number of reports for a given scenario, suggesting a within-subject
    design.  This is a simple diagnostic, not a formal structural-zero test.

    Args:
        groups: Mapping ``(strategy, scenario) -> rewards``.
        scenario: Scenario name to check.
        strategy_a: First strategy name.
        strategy_b: Second strategy name.

    Returns:
        ``True`` if counts match and are >= 2.
    """
    n_a = len(groups.get((strategy_a, scenario), []))
    n_b = len(groups.get((strategy_b, scenario), []))
    return n_a >= 2 and n_b >= 2 and n_a == n_b


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
        mean_governance_latency: Mean governance cycle duration in
            seconds, averaged across seeds. ``0.0`` for the baseline
            strategies, which run no cycle to time.
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
    mean_governance_latency: float = 0.0


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
                mean_governance_latency=statistics.mean([r.governance_latency_avg for r in reps]),
            )
        )
    return results


def compute_effect_sizes(
    aggregates: list[StrategyAggregate],
    reports: list[ExperimentReport],
    alpha: float = 0.05,
) -> list[dict]:
    """Compute Cohen's d and Mann-Whitney U with multiple-test correction.

    For each scenario, governance rewards are compared against every
    baseline using Cohen's d (parametric effect size, with CI and
    normality check) and Mann-Whitney U (non-parametric test, exact
    p-value when n < 8).  Raw p-values are corrected via both Bonferroni
    and Holm-Bonferroni.  A paired-design heuristic is noted.

    Args:
        aggregates: Aggregates (used to determine which scenarios exist).
        reports: Full report list (used to access raw rewards per group).
        alpha: Family-wise error rate (default 0.05).

    Returns:
        List of dicts with keys ``scenario``, ``governance_vs``, ``cohens_d``,
        ``cohens_d_ci``, ``cohens_d_se``, ``mannwhitney_u``, ``p_value_raw``,
        ``p_value_corrected``, ``p_value_holm``, ``significant``,
        ``significant_holm``, ``n_governance``, ``n_baseline``, ``paired``,
        ``normality_warning``, ``interpretation``. A scenario-baseline pair
        with no runs on either side yields no entry, and is not counted in
        the correction family — an arm that was never run is not a test that
        was performed.
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
            if not control_rewards or not treatment_rewards:
                continue
            d = _cohens_d(control_rewards, treatment_rewards)
            d_ci = _cohens_d_ci(control_rewards, treatment_rewards)

            normality = _shapiro_wilk(control_rewards + treatment_rewards, alpha)
            normality_warning = (
                "data non-normal; Cohen's d CI is approximate" if not normality["normal"] else None
            )

            if max(len(control_rewards), len(treatment_rewards)) <= 8:
                u_stat, p_raw = _mannwhitney_u_exact(control_rewards, treatment_rewards)
            else:
                u_stat, p_raw = _mannwhitney_u(control_rewards, treatment_rewards)

            raw_p_values.append(p_raw)

            paired = _is_paired(groups, scenario, governance_key, bl)

            effect_sizes.append(
                {
                    "scenario": scenario,
                    "governance_vs": bl,
                    "cohens_d": round(d, 3),
                    "cohens_d_ci": [d_ci["ci_lower"], d_ci["ci_upper"]],
                    "cohens_d_se": d_ci["se_d"],
                    "mannwhitney_u": u_stat,
                    "p_value_raw": p_raw,
                    "n_governance": len(control_rewards),
                    "n_baseline": len(treatment_rewards),
                    "paired": paired,
                    "normality_warning": normality_warning,
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
    holm_corrections = _holm_bonferroni_correct(raw_p_values, alpha)
    for es, corr, hcorr in zip(effect_sizes, corrections, holm_corrections):
        es["p_value_corrected"] = corr["corrected_p"]
        es["significant"] = corr["significant"]
        es["p_value_holm"] = hcorr["corrected_p"]
        es["significant_holm"] = hcorr["significant"]

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
                "mean_governance_latency_seconds",
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
                    round(a.mean_governance_latency, 9),
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
                "mean_governance_latency_seconds": a.mean_governance_latency,
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
