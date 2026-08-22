import math
import os
import re
import tempfile
from pathlib import Path

from src.nomos.benchmarks.analysis import (
    _MIN_REPORTABLE_P,
    _WILCOXON_EXACT_MAX_N,
    StrategyAggregate,
    _bonferroni_correct,
    _bootstrap_ci,
    _cohens_d,
    _cohens_d_ci,
    _detect_reward_hacking,
    _holm_bonferroni_correct,
    _is_paired,
    _mannwhitney_u,
    _mannwhitney_u_exact,
    _shapiro_wilk,
    _wilcoxon_signed_rank,
    aggregate_reports,
    compute_effect_sizes,
    detect_hacking_episodes,
    export_results_json,
    export_summary_csv,
    run_analysis,
)
from src.nomos.experiments.base import ExperimentMetrics
from src.nomos.experiments.metrics import ExperimentReport


def _make_report(name, reward, deadlocks=0, violations=0, steps=100, drift=0.0, step_records=None):
    metrics = ExperimentMetrics()
    metrics.total_reward = reward
    metrics.deadlock_count = deadlocks
    metrics.constraint_violations = violations
    metrics.total_steps = steps
    metrics.identity_drift = [drift]
    meta = {"strategy": "governance", "scenario": "GridWorld", "seed": 0}
    if step_records:
        meta["step_records"] = step_records
    report = ExperimentReport(
        name=name,
        total_steps=steps,
        total_reward=reward,
        avg_reward_per_step=reward / max(steps, 1),
        deadlock_count=deadlocks,
        deadlock_rate=deadlocks / max(steps, 1),
        constraint_violations=violations,
        veto_count=0,
        final_identity_drift=drift,
        governance_latency_avg=0.0,
        metadata=meta,
    )
    return report


class TestBootstrapCI:
    def test_single_value(self):
        lo, hi = _bootstrap_ci([5.0])
        assert lo == 5.0
        assert hi == 5.0

    def test_empty(self):
        lo, hi = _bootstrap_ci([])
        assert lo == 0.0
        assert hi == 0.0

    def test_range_contains_mean(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        lo, hi = _bootstrap_ci(values, n_resamples=1000)
        assert lo <= 3.0 <= hi


class TestCohensD:
    def test_identical_groups(self):
        d = _cohens_d([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert d == 0.0

    def test_positive_when_control_higher(self):
        d = _cohens_d([5.0, 6.0, 7.0], [1.0, 2.0, 3.0])
        assert d > 0.8

    def test_negative_when_treatment_higher(self):
        d = _cohens_d([1.0, 2.0, 3.0], [5.0, 6.0, 7.0])
        assert d < -0.8

    def test_small_samples(self):
        d = _cohens_d([1.0], [2.0])
        assert math.isnan(d)

    def test_zero_variance(self):
        d = _cohens_d([5.0, 5.0, 5.0], [3.0, 3.0, 3.0])
        assert math.isnan(d)


class TestMannWhitneyU:
    def test_identical_groups(self):
        u, p = _mannwhitney_u([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
        assert u == 8.0
        assert p > 0.9

    def test_separated_groups(self):
        u, p = _mannwhitney_u([5.0, 6.0, 7.0], [1.0, 2.0, 3.0])
        assert u == 0.0
        assert p < 0.05

    def test_reversed_groups_same_u(self):
        u1, p1 = _mannwhitney_u([5.0, 6.0], [1.0, 2.0])
        u2, p2 = _mannwhitney_u([1.0, 2.0], [5.0, 6.0])
        assert u1 == u2
        assert p1 == p2

    def test_insufficient_samples(self):
        u, p = _mannwhitney_u([1.0], [2.0])
        assert u == 0.0
        assert p == 1.0

    def test_empty_group(self):
        u, p = _mannwhitney_u([], [1.0, 2.0])
        assert u == 0.0
        assert p == 1.0

    def test_ties_reduce_u(self):
        u, p = _mannwhitney_u([3.0, 3.0, 3.0], [1.0, 2.0, 4.0])
        assert u >= 0.0

    def test_crossed_distributions(self):
        u, p = _mannwhitney_u(
            [1.0, 3.0, 5.0, 7.0],
            [2.0, 4.0, 6.0, 8.0],
        )
        assert u > 0.0
        assert p > 0.05


class TestMannWhitneyUExact:
    def test_identical_small(self):
        u, p = _mannwhitney_u_exact([1.0, 2.0], [1.0, 2.0])
        assert p > 0.05

    def test_separated_small(self):
        u, p = _mannwhitney_u_exact([5.0, 6.0], [1.0, 2.0])
        assert u == 0.0
        assert abs(p - 2.0 / 6.0) < 1e-12

    def test_falls_back_large(self):
        u, p = _mannwhitney_u_exact(list(range(10)), list(range(10, 20)))
        assert p < 0.05

    def test_insufficient_samples(self):
        u, p = _mannwhitney_u_exact([1.0], [2.0])
        assert u == 0.0
        assert p == 1.0


class TestHolmBonferroni:
    def test_single_comparison(self):
        results = _holm_bonferroni_correct([0.01])
        assert results[0]["corrected_p"] == 0.01
        assert results[0]["significant"] is True
        assert results[0]["method"] == "holm"

    def test_less_conservative_than_bonferroni(self):
        p_vals = [0.01, 0.03, 0.04]
        bonf = _bonferroni_correct(p_vals)
        holm = _holm_bonferroni_correct(p_vals)
        for b, h in zip(bonf, holm):
            assert h["corrected_p"] <= b["corrected_p"]

    def test_two_strong_signals(self):
        results = _holm_bonferroni_correct([0.01, 0.01], alpha=0.05)
        # rank 1: 0.01 * 2 = 0.02; rank 2: 0.01 * 1 = 0.01
        assert results[0]["corrected_p"] == 0.02
        assert results[0]["significant"] is True
        assert results[1]["corrected_p"] == 0.01

    def test_first_significant_rest_not(self):
        p_vals = [0.01, 0.04, 0.10]
        results = _holm_bonferroni_correct(p_vals, alpha=0.05)
        assert results[0]["corrected_p"] == 0.03
        assert results[0]["significant"] is True
        # rank 2: 0.04 * 2 = 0.08 > 0.05
        assert results[1]["significant"] is False
        assert results[2]["significant"] is False

    def test_empty(self):
        assert _holm_bonferroni_correct([]) == []

    def test_custom_alpha(self):
        results = _holm_bonferroni_correct([0.02, 0.02], alpha=0.01)
        assert results[0]["significant"] is False

    def test_rank_tracking(self):
        results = _holm_bonferroni_correct([0.03, 0.01, 0.02])
        for r in results:
            assert 1 <= r["rank"] <= 3


class TestCohensDCI:
    def test_identical_groups(self):
        ci = _cohens_d_ci([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert ci["d"] == 0.0

    def test_large_effect(self):
        ci = _cohens_d_ci([5.0, 6.0, 7.0], [1.0, 2.0, 3.0])
        assert ci["d"] > 0.5

    def test_small_samples(self):
        ci = _cohens_d_ci([1.0], [2.0])
        assert all(math.isnan(v) for v in ci.values())

    def test_ci_structure(self):
        ci = _cohens_d_ci([1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0])
        for key in ("d", "ci_lower", "ci_upper", "se_d"):
            assert key in ci

    def test_ci_contains_d(self):
        ci = _cohens_d_ci([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0])
        assert ci["ci_lower"] <= ci["d"] <= ci["ci_upper"]


class TestShapiroWilk:
    def test_normal_data(self):
        sample = [0.5, 0.2, -0.3, 0.8, -0.1, 0.0, 0.4, 0.6, 0.1, -0.4]
        result = _shapiro_wilk(sample)
        assert "W" in result
        assert "p_value" in result
        assert "normal" in result

    def test_uniform_approx_normal_enough(self):
        result = _shapiro_wilk([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result["normal"] is True

    def test_extreme_outlier_detected(self):
        sample = [0.0] * 5 + [100.0]
        result = _shapiro_wilk(sample)
        # 6 values with one extreme outlier should be non-normal
        assert result["normal"] is False

    def test_too_small(self):
        result = _shapiro_wilk([1.0, 2.0])
        assert result["normal"] is True
        assert result["warning"] == "n < 3"

    def test_constant_values(self):
        result = _shapiro_wilk([5.0, 5.0, 5.0, 5.0])
        assert result["normal"] is True

    def test_returns_warning_keys(self):
        result = _shapiro_wilk([1.0, 2.0, 3.0, 4.0, 5.0])
        for key in ("W", "p_value", "normal", "warning"):
            assert key in result


class TestIsPaired:
    def test_matched_seeds_paired(self):
        groups = {
            ("gov", "A"): {0: [1.0], 1: [2.0], 2: [3.0]},
            ("ran", "A"): {0: [4.0], 1: [5.0], 2: [6.0]},
        }
        assert _is_paired(groups, "A", "gov", "ran") is True

    def test_unequal_counts_not_paired(self):
        groups = {
            ("gov", "A"): {0: [1.0], 1: [2.0], 2: [3.0]},
            ("ran", "A"): {0: [4.0], 1: [5.0]},
        }
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_empty_group_not_paired(self):
        groups = {("gov", "A"): {}}
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_different_scenario(self):
        groups = {("gov", "A"): {0: [1.0], 1: [2.0]}, ("ran", "B"): {0: [3.0], 1: [4.0]}}
        assert _is_paired(groups, "A", "gov", "ran") is False


class TestBonferroniCorrection:
    def test_single_comparison(self):
        results = _bonferroni_correct([0.01])
        assert results[0]["raw_p"] == 0.01
        assert results[0]["corrected_p"] == 0.01
        assert results[0]["significant"] is True

    def test_multiple_comparisons_stricter(self):
        results = _bonferroni_correct([0.01, 0.01], alpha=0.05)
        assert results[0]["corrected_p"] == 0.02
        assert results[0]["significant"] is True
        assert results[1]["corrected_p"] == 0.02
        assert results[1]["significant"] is True

    def test_multiple_comparisons_insignificant(self):
        results = _bonferroni_correct([0.03, 0.03], alpha=0.05)
        assert results[0]["corrected_p"] == 0.06
        assert results[0]["significant"] is False

    def test_capped_at_one(self):
        results = _bonferroni_correct([0.6, 0.6], alpha=0.05)
        assert results[0]["corrected_p"] == 1.0
        assert results[0]["significant"] is False

    def test_empty(self):
        assert _bonferroni_correct([]) == []

    def test_custom_alpha(self):
        results = _bonferroni_correct([0.02, 0.02], alpha=0.01)
        c = results[0]["corrected_p"]
        assert c == 0.04
        assert results[0]["significant"] is False

    def test_mixed_values(self):
        results = _bonferroni_correct([0.001, 0.04, 0.5], alpha=0.05)
        assert results[0]["significant"] is True
        assert results[1]["significant"] is False
        assert results[2]["significant"] is False


class TestDetectRewardHacking:
    def test_no_violations_no_episodes(self):
        records = [{"reward": 1.0, "violations": 0} for _ in range(20)]
        episodes = _detect_reward_hacking(records)
        assert episodes == []

    def test_violation_without_spike_no_episode(self):
        records = [{"reward": 1.0, "violations": 0} for _ in range(20)]
        records[15]["violations"] = 1
        episodes = _detect_reward_hacking(records)
        assert episodes == []

    def test_violation_with_spike_detected(self):
        records = [{"reward": 1.0, "violations": 0} for _ in range(20)]
        for i in range(16, 20):
            records[i]["reward"] = 10.0
        records[18]["violations"] = 1
        episodes = _detect_reward_hacking(records)
        assert len(episodes) >= 1
        assert episodes[0]["violation_count"] >= 1

    def test_empty_records(self):
        assert _detect_reward_hacking([]) == []


class TestAggregateReports:
    def test_single_report(self):
        reports = [_make_report("test", 100.0)]
        aggregates = aggregate_reports(reports)
        assert len(aggregates) == 1
        assert aggregates[0].mean_reward == 100.0
        assert aggregates[0].num_seeds == 1

    def test_multiple_reports_same_group(self):
        reports = [
            _make_report("r1", 50.0),
            _make_report("r2", 70.0),
        ]
        aggregates = aggregate_reports(reports)
        assert len(aggregates) == 1
        assert aggregates[0].mean_reward == 60.0

    def test_different_groups(self):
        r1 = _make_report("r1", 50.0)
        r1.metadata["strategy"] = "governance"
        r1.metadata["scenario"] = "A"
        r2 = _make_report("r2", 70.0)
        r2.metadata["strategy"] = "random"
        r2.metadata["scenario"] = "A"
        aggregates = aggregate_reports([r1, r2])
        assert len(aggregates) == 2

    def test_empty_reports(self):
        assert aggregate_reports([]) == []

    def test_strategy_aggregate_dataclass(self):
        agg = StrategyAggregate(
            strategy="test", scenario="test", num_seeds=5, mean_reward=10.0, std_reward=2.0,
            mean_deadlocks=1.0, mean_violations=0.5, ci_lower=8.0, ci_upper=12.0,
        )
        assert agg.mean_reward == 10.0
        assert agg.std_reward == 2.0


class TestComputeEffectSizes:
    def test_governance_vs_baselines(self):
        reports = []
        for strategy in ["governance", "random"]:
            for i in range(5):
                base = 50.0 if strategy == "governance" else 30.0
                r = _make_report(f"{strategy}_n", base + i)
                r.metadata["strategy"] = strategy
                reports.append(r)
        aggregates = aggregate_reports(reports)
        es = compute_effect_sizes(aggregates, reports)
        assert len(es) >= 1
        d = [e for e in es if e["governance_vs"] == "random"]
        assert len(d) == 1
        assert d[0]["cohens_d"] > 0

    def test_new_fields_present(self):
        reports = []
        for strategy in ["governance", "random"]:
            for i in range(5):
                r = _make_report(f"{strategy}_n", 40.0 + i)
                r.metadata["strategy"] = strategy
                reports.append(r)
        aggregates = aggregate_reports(reports)
        es = compute_effect_sizes(aggregates, reports)
        entry = es[0]
        assert "mannwhitney_u" in entry
        assert "p_value_raw" in entry
        assert "p_value_corrected" in entry
        assert "significant" in entry
        assert "p_value_holm" in entry
        assert "significant_holm" in entry
        assert "cohens_d_ci" in entry
        assert "cohens_d_se" in entry
        assert "normality_warning" in entry
        assert "paired" in entry
        assert isinstance(entry["significant"], bool)
        assert isinstance(entry["significant_holm"], bool)
        assert isinstance(entry["paired"], bool)

    def test_bonferroni_applied(self):
        reports = []
        for strategy in ["governance", "random", "monolithic_rl"]:
            for i in range(20):
                r = _make_report(f"{strategy}_n", 50.0 + i)
                r.metadata["strategy"] = strategy
                r.metadata["scenario"] = "GridWorld"
                reports.append(r)
        aggregates = aggregate_reports(reports)
        es = compute_effect_sizes(aggregates, reports)
        assert {e["governance_vs"] for e in es} == {"random", "monolithic_rl"}
        for entry in es:
            assert 0.0 <= entry["p_value_raw"] <= 1.0
            assert entry["p_value_corrected"] >= entry["p_value_raw"]
            assert entry["p_value_holm"] >= entry["p_value_raw"]
            assert entry["p_value_holm"] <= entry["p_value_corrected"]

    def test_baseline_without_runs_yields_no_row(self):
        reports = []
        for strategy in ["governance", "random"]:
            for i in range(5):
                r = _make_report(f"{strategy}_n", 50.0 + i)
                r.metadata["strategy"] = strategy
                r.metadata["scenario"] = "GridWorld"
                reports.append(r)
        aggregates = aggregate_reports(reports)
        es = compute_effect_sizes(aggregates, reports)
        assert [e["governance_vs"] for e in es] == ["random"]
        assert all(e["n_baseline"] > 0 for e in es)

    def test_empty_reports(self):
        es = compute_effect_sizes([], [])
        assert es == []


class TestDetectHackingEpisodes:
    def test_no_episodes(self):
        records = [{"reward": 1.0, "violations": 0} for _ in range(20)]
        r = _make_report("test", 20.0, step_records=records)
        episodes = detect_hacking_episodes([r])
        assert episodes == []

    def test_tags_with_metadata(self):
        records = [{"reward": 1.0, "violations": 0} for _ in range(20)]
        for i in range(16, 20):
            records[i]["reward"] = 10.0
        records[18]["violations"] = 1
        r = _make_report("test", 40.0, step_records=records)
        r.metadata["strategy"] = "governance"
        r.metadata["scenario"] = "GridWorld"
        r.metadata["seed"] = 42
        episodes = detect_hacking_episodes([r])
        if episodes:
            assert episodes[0].get("strategy") == "governance"
            assert episodes[0].get("scenario") == "GridWorld"

    def test_empty_reports(self):
        assert detect_hacking_episodes([]) == []


class TestExportFunctions:
    def test_export_summary_csv(self):
        aggregates = [StrategyAggregate("gov", "GridWorld", 5, 100.0, 10.0, 0.0, 0.0, 90.0, 110.0)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "summary.csv")
            export_summary_csv(aggregates, path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "strategy" in content
            assert "gov" in content

    def test_export_results_json(self):
        r = _make_report("test", 100.0)
        agg = StrategyAggregate("gov", "GW", 1, 100.0, 0.0, 0.0, 0.0, 90.0, 110.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            export_results_json([r], [agg], [], [], path)
            assert os.path.exists(path)
            import json

            with open(path) as f:
                data = json.load(f)
            assert "aggregates" in data
            assert len(data["aggregates"]) == 1


class TestRunAnalysis:
    def test_analysis_pipeline(self):
        reports = []
        for strategy in ["governance", "random"]:
            for _ in range(3):
                records = [{"reward": 1.0, "violations": 0} for _ in range(10)]
                r = _make_report(
                    f"{strategy}_n", 50.0 if strategy == "governance" else 30.0,
                    step_records=records,
                )
                r.metadata["strategy"] = strategy
                r.metadata["scenario"] = "GridWorld"
                reports.append(r)

        with tempfile.TemporaryDirectory() as tmp:
            result = run_analysis(reports, output_dir=tmp)
            assert "aggregates" in result
            assert "effect_sizes" in result
            assert "hacking_episodes" in result
            assert "summary_csv" in result
            assert "results_json" in result
            assert len(result["effect_sizes"]) > 0

    def test_empty_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_analysis([], output_dir=tmp)
            assert result["aggregates"] == []
            assert result["effect_sizes"] == []


class TestGovernanceLatencyExport:
    """The measured latency must survive the exporters (#293)."""

    def _reports(self, *latencies):
        reports = []
        for i, latency in enumerate(latencies):
            r = _make_report(f"r{i}", 50.0)
            r.governance_latency_avg = latency
            reports.append(r)
        return reports

    def test_aggregate_means_the_per_seed_latencies(self):
        aggregates = aggregate_reports(self._reports(0.004, 0.006))
        assert aggregates[0].mean_governance_latency == 0.005

    def test_baseline_reports_aggregate_to_zero(self):
        aggregates = aggregate_reports(self._reports(0.0, 0.0))
        assert aggregates[0].mean_governance_latency == 0.0

    def test_summary_csv_carries_the_latency_column(self):
        import csv

        aggregates = aggregate_reports(self._reports(0.000025))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "summary.csv")
            export_summary_csv(aggregates, path)
            with open(path, newline="") as f:
                header, row = list(csv.reader(f))

        assert header[-1] == "mean_governance_latency_seconds"
        assert float(row[-1]) == 0.000025

    def test_results_json_carries_the_latency_field(self):
        import json

        aggregates = aggregate_reports(self._reports(0.000025))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            export_results_json([], aggregates, [], [], path)
            with open(path) as f:
                data = json.load(f)

        assert data["aggregates"][0]["mean_governance_latency_seconds"] == 0.000025

    def test_run_analysis_publishes_a_nonzero_latency(self):
        import json

        with tempfile.TemporaryDirectory() as tmp:
            result = run_analysis(self._reports(0.004, 0.006), output_dir=tmp)
            with open(result["results_json"]) as f:
                data = json.load(f)

        assert data["aggregates"][0]["mean_governance_latency_seconds"] == 0.005


def _cell(strategy, scenario, rewards, seeds=None):
    """Build one strategy-scenario cell, one report per seed."""
    seeds = list(range(len(rewards))) if seeds is None else seeds
    out = []
    for seed, reward in zip(seeds, rewards):
        r = _make_report(f"{strategy}_{scenario}_{seed}", reward)
        r.metadata["strategy"] = strategy
        r.metadata["scenario"] = scenario
        r.metadata["seed"] = seed
        out.append(r)
    return out


class TestDegenerateEffectSizes:
    """The published TemptationBank cell: two constants 6863.0 apart."""

    def test_zero_pooled_variance_with_separation_is_undefined(self):
        d = _cohens_d([1998.0] * 20, [-4865.0] * 20)
        assert math.isnan(d)

    def test_identical_constants_really_are_no_effect(self):
        assert _cohens_d([5.0] * 4, [5.0] * 4) == 0.0

    def test_ci_around_an_undefined_d_is_undefined(self):
        ci = _cohens_d_ci([1998.0] * 20, [-4865.0] * 20)
        assert all(math.isnan(v) for v in ci.values())

    def test_record_marks_the_gap_undefined_and_keeps_the_direction(self):
        reports = _cell("governance", "TemptationBank", [1998.0] * 20)
        reports += _cell("monolithic_rl", "TemptationBank", [-4865.0] * 20)
        es = compute_effect_sizes(aggregate_reports(reports), reports)

        (entry,) = [e for e in es if e["governance_vs"] == "monolithic_rl"]
        assert entry["interpretation"] == "undefined (zero pooled variance)"
        assert entry["cohens_d"] is None
        assert entry["cohens_d_ci"] == [None, None]
        assert entry["cohens_d_se"] is None
        assert entry["mean_governance"] == 1998.0
        assert entry["mean_baseline"] == -4865.0
        assert entry["mean_diff"] == 6863.0

    def test_equal_constants_keep_the_point_estimate_but_lose_the_interval(self):
        ci = _cohens_d_ci([5.0] * 4, [5.0] * 4)
        assert _cohens_d([5.0] * 4, [5.0] * 4) == 0.0
        assert all(math.isnan(v) for v in ci.values())

    def test_record_publishes_no_interval_on_a_deterministic_zero_effect(self):
        reports = _cell("governance", "DeadlockMaze", [0.0] * 20)
        reports += _cell("random", "DeadlockMaze", [0.0] * 20)
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["cohens_d"] == 0.0
        assert entry["interpretation"] == "negligible"
        assert entry["cohens_d_ci"] == [None, None]
        assert entry["cohens_d_se"] is None

    def test_a_measured_zero_effect_keeps_its_interval(self):
        rewards = [float(i) for i in range(20)]
        reports = _cell("governance", "GridWorld", rewards)
        reports += _cell("veto_only", "GridWorld", rewards)
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["cohens_d"] == 0.0
        assert entry["cohens_d_se"] is not None
        assert entry["cohens_d_ci"] != [None, None]

    def test_a_losing_degenerate_cell_is_distinguishable_from_a_winning_one(self):
        reports = _cell("governance", "S", [10.0] * 6)
        reports += _cell("random", "S", [1.0] * 6)
        reports += _cell("veto_only", "S", [99.0] * 6)
        es = {
            e["governance_vs"]: e for e in compute_effect_sizes(aggregate_reports(reports), reports)
        }

        assert es["random"]["interpretation"] == es["veto_only"]["interpretation"]
        assert es["random"]["mean_diff"] == 9.0
        assert es["veto_only"]["mean_diff"] == -89.0


class TestPValuePrecision:
    def test_normal_approximation_keeps_a_sub_1e_4_tail(self):
        u, p = _mannwhitney_u([1998.0] * 20, [-4865.0] * 20)
        assert u == 0.0
        assert p == 4.2380554260794744e-10

    def test_exact_path_is_not_rounded_to_four_places(self):
        u, p = _mannwhitney_u_exact([5.0, 6.0, 7.0, 8.0], [1.0, 2.0, 3.0, 4.0])
        assert u == 0.0
        assert abs(p - 2.0 / 70.0) < 1e-15
        assert p != round(p, 4)

    def test_an_underflowed_tail_is_floored_rather_than_zero(self):
        # |z| passes 38.5 here, so math.erfc really does return 0.0.
        u, p = _mannwhitney_u(
            [float(i) for i in range(1000)], [float(i) + 1e4 for i in range(1000)]
        )
        assert u == 0.0
        assert p > 0.0
        assert p == _MIN_REPORTABLE_P

    def test_holm_keeps_full_precision(self):
        results = _holm_bonferroni_correct([1e-10, 0.5])
        assert results[0]["corrected_p"] == 2e-10

    def test_bonferroni_keeps_full_precision(self):
        results = _bonferroni_correct([1e-10, 0.5])
        assert results[0]["corrected_p"] == 2e-10


class TestSignificanceInvariant:
    """No record may claim zero probability and significance at once."""

    @staticmethod
    def _suite():
        reports = _cell("governance", "TemptationBank", [1998.0] * 20)
        reports += _cell("monolithic_rl", "TemptationBank", [-4865.0] * 20)
        reports += _cell("static_masking", "TemptationBank", [2000.0] * 20)
        reports += _cell("governance", "GridWorld", [float(i) for i in range(20)])
        reports += _cell("random", "GridWorld", [float(i) - 100 for i in range(20)])
        return reports

    def test_no_zero_raw_p_is_flagged_significant(self):
        reports = self._suite()
        es = compute_effect_sizes(aggregate_reports(reports), reports)
        assert es
        assert not any(e["p_value_raw"] == 0.0 and e["significant_holm"] for e in es)
        assert not any(e["p_value_raw"] == 0.0 and e["significant"] for e in es)

    def test_the_invariant_is_not_vacuous(self):
        reports = self._suite()
        es = compute_effect_sizes(aggregate_reports(reports), reports)
        tiny = [e for e in es if e["significant_holm"] and e["p_value_raw"] < 1e-4]
        assert tiny, "expected at least one genuinely tiny significant p-value"
        assert all(e["p_value_raw"] > 0.0 for e in tiny)


class TestSeedKeyedPairing:
    def test_equal_counts_over_disjoint_seeds_are_not_paired(self):
        groups = {
            ("gov", "A"): {0: [1.0], 1: [2.0], 2: [3.0]},
            ("ran", "A"): {100: [4.0], 101: [5.0], 102: [6.0]},
        }
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_a_repeated_seed_inside_a_cell_is_not_paired(self):
        groups = {
            ("gov", "A"): {0: [1.0, 2.0], 1: [3.0, 4.0]},
            ("ran", "A"): {0: [5.0, 6.0], 1: [7.0, 8.0]},
        }
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_unlabelled_seeds_are_not_paired(self):
        groups = {("gov", "A"): {None: [1.0, 2.0]}, ("ran", "A"): {None: [3.0, 4.0]}}
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_record_reports_unpaired_when_the_seed_sets_differ(self):
        reports = _cell("governance", "S", [10.0, 11.0, 12.0, 13.0], seeds=[0, 1, 2, 3])
        reports += _cell("random", "S", [1.0, 2.0, 3.0, 4.0], seeds=[7, 8, 9, 10])
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["paired"] is False
        assert entry["wilcoxon_w"] is None
        assert entry["wilcoxon_p"] is None
        assert entry["wilcoxon_method"] is None

    def test_record_reports_paired_and_tests_it_when_seeds_match(self):
        reports = _cell("governance", "S", [10.0, 11.0, 12.0, 13.0], seeds=[0, 1, 2, 3])
        reports += _cell("random", "S", [1.0, 2.0, 3.0, 4.0], seeds=[0, 1, 2, 3])
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["paired"] is True
        assert entry["wilcoxon_method"] == "exact"
        assert entry["wilcoxon_p"] == 2.0 / 2**4


class TestWilcoxonPairCounts:
    """The p-value rests on the surviving pairs, so the record says how many."""

    def test_dropped_ties_are_visible_on_the_record(self):
        seeds = list(range(20))
        governance = [5.0] * 12 + [5.0 + k for k in range(1, 9)]
        reports = _cell("governance", "S", governance, seeds=seeds)
        reports += _cell("random", "S", [5.0] * 20, seeds=seeds)
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["n_governance"] == 20
        assert entry["wilcoxon_n_pairs"] == 8
        assert entry["wilcoxon_n_zero_diffs"] == 12
        assert entry["wilcoxon_p"] == 2.0 / 2**8

    def test_an_unpaired_comparison_reports_no_counts(self):
        reports = _cell("governance", "S", [10.0, 11.0, 12.0, 13.0], seeds=[0, 1, 2, 3])
        reports += _cell("random", "S", [1.0, 2.0, 3.0, 4.0], seeds=[7, 8, 9, 10])
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        assert entry["paired"] is False
        assert entry["wilcoxon_n_pairs"] is None
        assert entry["wilcoxon_n_zero_diffs"] is None


class TestWilcoxonSignedRank:
    @staticmethod
    def _brute_force(diffs):
        import itertools

        nonzero = [d for d in diffs if d != 0]
        n = len(nonzero)
        order = sorted(range(n), key=lambda i: abs(nonzero[i]))
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and abs(nonzero[order[j]]) == abs(nonzero[order[i]]):
                j += 1
            for k in range(i, j):
                ranks[order[k]] = (i + 1 + j) / 2.0
            i = j
        total = sum(ranks)
        w_plus = sum(ranks[i] for i in range(n) if nonzero[i] > 0)
        w = min(w_plus, total - w_plus)
        extreme = 0
        for signs in itertools.product((0, 1), repeat=n):
            t = sum(ranks[i] for i in range(n) if signs[i])
            if min(t, total - t) <= w + 1e-12:
                extreme += 1
        return w, min(1.0, extreme / 2**n)

    def test_exact_distribution_matches_brute_force_enumeration(self):
        cases = [
            [1.0, 2.0, 3.0, 4.0],
            [-1.0, -2.0, 3.0, 4.0, 5.0],
            [2.0, 2.0, 2.0, -2.0, 5.0],
            [0.0, 1.0, -1.0, 3.0, 0.0, 4.0],
            [-5.0, -4.0, -3.0, -2.0, -1.0, 6.0, 7.0],
        ]
        for diffs in cases:
            result = _wilcoxon_signed_rank(diffs, [0.0] * len(diffs))
            expected_w, expected_p = self._brute_force(diffs)
            assert result["method"] == "exact"
            assert abs(result["w"] - expected_w) < 1e-12, diffs
            assert abs(result["p_value"] - expected_p) < 1e-12, diffs

    def test_every_pair_favouring_one_side_gives_two_over_two_to_the_n(self):
        result = _wilcoxon_signed_rank([float(i) for i in range(1, 11)], [0.0] * 10)
        assert result["w"] == 0.0
        assert result["n_pairs"] == 10
        assert result["p_value"] == 2.0 / 2**10

    def test_a_deterministic_cell_reduces_to_a_sign_test(self):
        result = _wilcoxon_signed_rank([1998.0] * 20, [-4865.0] * 20)
        assert result["method"] == "exact"
        assert result["w"] == 0.0
        assert result["p_value"] == 2.0 / 2**20

    def test_all_zero_differences_are_no_evidence(self):
        result = _wilcoxon_signed_rank([3.0] * 5, [3.0] * 5)
        assert result["method"] == "all-zero-differences"
        assert result["p_value"] == 1.0
        assert result["n_zero_diffs"] == 5

    def test_dropped_zero_pairs_are_counted(self):
        result = _wilcoxon_signed_rank([1.0, 2.0, 3.0, 4.0], [1.0, 0.0, 3.0, 0.0])
        assert result["n_pairs"] == 2
        assert result["n_zero_diffs"] == 2

    def test_unequal_lengths_are_undefined(self):
        result = _wilcoxon_signed_rank([1.0, 2.0], [1.0])
        assert result["w"] is None
        assert result["p_value"] is None
        assert result["method"] == "undefined"

    def test_large_samples_use_the_normal_approximation(self):
        result = _wilcoxon_signed_rank(
            [float(i) + 5.0 for i in range(30)], [float(i) for i in range(30)]
        )
        assert result["method"] == "normal"
        assert result["n_pairs"] == 30
        assert 0.0 < result["p_value"] < 1e-6


APPENDIX_D = Path(__file__).parent.parent / "book" / "appendix-d-experiment-protocol.md"


class TestPublishedStatisticsClaims:
    """Appendix D.5 spells out the record and the method; hold it to the code.

    Both claims are hand-maintained prose about a machine-generated record,
    which is exactly the kind of sentence that goes stale beneath its subject.
    """

    @staticmethod
    def _appendix_text():
        return APPENDIX_D.read_text(encoding="utf-8")

    def test_the_documented_record_keys_are_the_emitted_ones(self):
        reports = _cell("governance", "S", [10.0, 11.0, 12.0, 13.0])
        reports += _cell("random", "S", [1.0, 2.0, 3.0, 4.0])
        (entry,) = compute_effect_sizes(aggregate_reports(reports), reports)

        sentence = next(
            line
            for line in self._appendix_text().splitlines()
            if line.startswith("Each entry returned by `compute_effect_sizes()` includes:")
        )
        documented = set(re.findall(r"`([a-z_]+)`", sentence)) - {"compute_effect_sizes()"}
        assert documented == set(entry)

    def test_the_documented_exact_wilcoxon_cutoff_is_the_code_constant(self):
        cutoff = re.search(
            r"exact null distribution up to (\d+) non-zero differences", self._appendix_text()
        )
        assert cutoff, "Appendix D.5 no longer states the Wilcoxon exact cutoff"
        assert int(cutoff.group(1)) == _WILCOXON_EXACT_MAX_N
