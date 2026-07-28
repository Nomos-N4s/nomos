import os
import tempfile

from src.governance.benchmarks.analysis import (
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
    aggregate_reports,
    compute_effect_sizes,
    detect_hacking_episodes,
    export_results_json,
    export_summary_csv,
    run_analysis,
)
from src.governance.experiments.base import ExperimentMetrics
from src.governance.experiments.metrics import ExperimentReport


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
        assert d == 0.0

    def test_zero_variance(self):
        d = _cohens_d([5.0, 5.0, 5.0], [3.0, 3.0, 3.0])
        assert d == 0.0


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
        assert p == 0.3333

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
        assert ci["d"] == 0.0

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
    def test_equal_counts_paired(self):
        groups = {("gov", "A"): [1, 2, 3], ("ran", "A"): [4, 5, 6]}
        assert _is_paired(groups, "A", "gov", "ran") is True

    def test_unequal_counts_not_paired(self):
        groups = {("gov", "A"): [1, 2, 3], ("ran", "A"): [4, 5]}
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_empty_group_not_paired(self):
        groups = {("gov", "A"): []}
        assert _is_paired(groups, "A", "gov", "ran") is False

    def test_different_scenario(self):
        groups = {("gov", "A"): [1, 2], ("ran", "B"): [3, 4]}
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
        assert len(es) == 4
        for entry in es:
            assert 0.0 <= entry["p_value_raw"] <= 1.0
            assert entry["p_value_corrected"] >= entry["p_value_raw"]
            assert entry["p_value_holm"] >= entry["p_value_raw"]
            assert entry["p_value_holm"] <= entry["p_value_corrected"]

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
