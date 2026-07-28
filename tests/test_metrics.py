import json

from src.governance.experiments.metrics import (
    ExperimentReport,
    compare_reports,
    generate_report,
)


class FakeExperimentMetrics:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestExperimentReport:
    def test_creation_minimal(self):
        r = ExperimentReport(
            name="test",
            total_steps=100,
            total_reward=50.0,
            avg_reward_per_step=0.5,
            deadlock_count=5,
            deadlock_rate=0.05,
            constraint_violations=2,
            veto_count=3,
            final_identity_drift=0.1,
            governance_latency_avg=0.01,
        )
        assert r.name == "test"
        assert r.total_steps == 100
        assert r.total_reward == 50.0

    def test_creation_zero_steps(self):
        r = ExperimentReport(
            name="empty",
            total_steps=0,
            total_reward=0.0,
            avg_reward_per_step=0.0,
            deadlock_count=0,
            deadlock_rate=0.0,
            constraint_violations=0,
            veto_count=0,
            final_identity_drift=0.0,
            governance_latency_avg=0.0,
        )
        assert r.total_steps == 0
        assert r.total_reward == 0.0

    def test_to_dict(self):
        r = ExperimentReport(
            name="d", total_steps=10, total_reward=5.0, avg_reward_per_step=0.5,
            deadlock_count=1, deadlock_rate=0.1, constraint_violations=0,
            veto_count=0, final_identity_drift=0.0, governance_latency_avg=0.0,
            metadata={"seed": 42},
        )
        d = r.to_dict()
        assert d["name"] == "d"
        assert d["total_steps"] == 10
        assert d["metadata"] == {"seed": 42}

    def test_to_json(self):
        r = ExperimentReport(
            name="j", total_steps=1, total_reward=1.0, avg_reward_per_step=1.0,
            deadlock_count=0, deadlock_rate=0.0, constraint_violations=0,
            veto_count=0, final_identity_drift=0.0, governance_latency_avg=0.0,
        )
        parsed = json.loads(r.to_json())
        assert parsed["name"] == "j"
        assert parsed["total_reward"] == 1.0


class TestGenerateReport:
    def test_generates_correctly(self):
        metrics = FakeExperimentMetrics(
            total_steps=200,
            total_reward=100.0,
            deadlock_count=10,
            constraint_violations=3,
            veto_count=5,
            identity_drift=[0.0, 0.05, 0.1],
            governance_latencies=[0.005, 0.007, 0.006],
        )
        r = generate_report("test_run", metrics, [])
        assert r.name == "test_run"
        assert r.total_steps == 200
        assert r.total_reward == 100.0
        assert r.avg_reward_per_step == 0.5
        assert r.deadlock_count == 10
        assert r.deadlock_rate == 0.05
        assert r.constraint_violations == 3
        assert r.veto_count == 5
        assert r.final_identity_drift == 0.1
        assert r.governance_latency_avg == 0.006

    def test_empty_identity_drift(self):
        metrics = FakeExperimentMetrics(
            total_steps=10, total_reward=5.0, deadlock_count=0,
            constraint_violations=0, veto_count=0,
            identity_drift=[], governance_latencies=[],
        )
        r = generate_report("no_drift", metrics, [])
        assert r.final_identity_drift == 0.0
        assert r.governance_latency_avg == 0.0

    def test_zero_steps_no_division_error(self):
        metrics = FakeExperimentMetrics(
            total_steps=0, total_reward=0.0, deadlock_count=0,
            constraint_violations=0, veto_count=0,
            identity_drift=[], governance_latencies=[],
        )
        r = generate_report("zero", metrics, [])
        assert r.avg_reward_per_step == 0.0
        assert r.deadlock_rate == 0.0


class TestCompareReports:
    def make_report(self, name, reward, deadlock_rate, violations, **kw):
        return ExperimentReport(
            name=name,
            total_steps=100,
            total_reward=reward * 100,
            avg_reward_per_step=reward,
            deadlock_count=int(deadlock_rate * 100),
            deadlock_rate=deadlock_rate,
            constraint_violations=violations,
            veto_count=kw.pop("veto_count", 0),
            final_identity_drift=kw.pop("drift", 0.0),
            governance_latency_avg=kw.pop("latency", 0.0),
            metadata=kw.pop("metadata", {}),
        )

    def test_baseline_vs_better(self):
        baseline = self.make_report("gov", reward=0.5, deadlock_rate=0.1, violations=5)
        better = self.make_report("mono", reward=0.8, deadlock_rate=0.05, violations=2)
        result = compare_reports([baseline, better])
        assert result["baseline"] == "gov"
        assert result["mono"]["reward_change"] == 60.0
        assert result["mono"]["deadlock_rate_change"] == -5.0
        assert result["mono"]["violations_change"] == -3

    def test_baseline_vs_worse(self):
        baseline = self.make_report("gov", reward=0.5, deadlock_rate=0.1, violations=2)
        worse = self.make_report("worse", reward=0.2, deadlock_rate=0.3, violations=10)
        result = compare_reports([baseline, worse])
        assert result["worse"]["reward_change"] == -60.0
        assert result["worse"]["deadlock_rate_change"] == 20.0
        assert result["worse"]["violations_change"] == 8

    def test_multiple_comparisons(self):
        baseline = self.make_report("gov", reward=0.5, deadlock_rate=0.1, violations=2)
        a = self.make_report("A", reward=0.6, deadlock_rate=0.05, violations=1)
        b = self.make_report("B", reward=0.4, deadlock_rate=0.2, violations=5)
        result = compare_reports([baseline, a, b])
        assert "A" in result
        assert "B" in result

    def test_zero_baseline_reward_no_division_error(self):
        baseline = self.make_report("gov", reward=0.0, deadlock_rate=0.0, violations=0)
        other = self.make_report("other", reward=0.0, deadlock_rate=0.1, violations=3)
        result = compare_reports([baseline, other])
        assert "reward_change" not in result["other"]
        assert result["other"]["deadlock_rate_change"] == 10.0
        assert result["other"]["violations_change"] == 3
