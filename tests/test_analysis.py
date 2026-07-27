import os
import tempfile
import pytest
from src.governance.benchmarks.analysis import (
    StrategyAggregate,
    _bootstrap_ci,
    _cohens_d,
    _detect_reward_hacking,
    aggregate_reports,
    compute_effect_sizes,
    detect_hacking_episodes,
    export_summary_csv,
    export_results_json,
    run_analysis,
)
from src.governance.experiments.metrics import ExperimentReport
from src.governance.experiments.base import ExperimentMetrics


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
