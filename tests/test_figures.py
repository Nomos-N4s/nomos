import os
import tempfile

from src.governance.benchmarks.figures import (
    _ci_to_error,
    generate_all_figures,
    plot_deadlock_frequency,
    plot_pareto_frontier,
    plot_reward_curves,
    plot_violation_rates,
)
from src.governance.experiments.metrics import ExperimentReport


def _make_report(name, reward, violations=0, deadlocks=0, drate=0.0, steps=100, scenario="A", strategy="gov"):
    return ExperimentReport(
        name=name,
        total_steps=steps,
        total_reward=reward,
        avg_reward_per_step=reward / max(steps, 1),
        deadlock_count=deadlocks,
        deadlock_rate=drate,
        constraint_violations=violations,
        veto_count=0,
        final_identity_drift=0.0,
        governance_latency_avg=0.0,
        metadata={
            "scenario": scenario,
            "strategy": strategy,
            "step_records": [{"reward": i * (reward / max(steps, 1)), "violations": 0} for i in range(steps)],
        },
    )


def test_ci_to_error_empty():
    lo, hi = _ci_to_error([])
    assert lo == [0.0]
    assert hi == [0.0]


def test_ci_to_error_single():
    lo, hi = _ci_to_error([5.0])
    assert lo == [0.0]
    assert hi == [0.0]


def test_ci_to_error_multiple():
    lo, hi = _ci_to_error([1.0, 2.0, 3.0, 4.0, 5.0])
    assert len(lo) == 1
    assert len(hi) == 1
    assert lo[0] >= 0
    assert hi[0] >= 0


class TestFiguresSmoke:
    """Smoke tests: each plot function runs without error and produces files."""

    _reports = [
        _make_report("r1", 100, 2, 0, 0.0, 100, "A", "gov"),
        _make_report("r2", 80, 5, 1, 0.01, 100, "A", "mono"),
        _make_report("r3", 150, 0, 0, 0.0, 100, "B", "gov"),
        _make_report("r4", 60, 8, 2, 0.02, 100, "B", "mono"),
        _make_report("r5", 90, 3, 0, 0.0, 100, "A", "rand"),
        _make_report("r6", 110, 1, 0, 0.0, 100, "B", "rand"),
    ]

    def test_plot_reward_curves(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot_reward_curves(self._reports, tmp)
            assert os.path.isfile(f"{tmp}/reward_curves.png")
            assert os.path.isfile(f"{tmp}/reward_curves.svg")

    def test_plot_violation_rates(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot_violation_rates(self._reports, tmp)
            assert os.path.isfile(f"{tmp}/violation_rates.png")
            assert os.path.isfile(f"{tmp}/violation_rates.svg")

    def test_plot_deadlock_frequency(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot_deadlock_frequency(self._reports, tmp)
            assert os.path.isfile(f"{tmp}/deadlock_frequency.png")
            assert os.path.isfile(f"{tmp}/deadlock_frequency.svg")

    def test_plot_pareto_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot_pareto_frontier(self._reports, tmp)
            assert os.path.isfile(f"{tmp}/pareto_frontier.png")
            assert os.path.isfile(f"{tmp}/pareto_frontier.svg")

    def test_generate_all_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_all_figures(self._reports, tmp)
            for f in ["reward_curves", "violation_rates", "deadlock_frequency", "pareto_frontier"]:
                assert os.path.isfile(f"{tmp}/{f}.png"), f"Missing {f}.png"
                assert os.path.isfile(f"{tmp}/{f}.svg"), f"Missing {f}.svg"

    def test_plot_reward_curves_single_strategy(self):
        reports = [self._reports[0]]
        with tempfile.TemporaryDirectory() as tmp:
            plot_reward_curves(reports, tmp)
            assert os.path.isfile(f"{tmp}/reward_curves.png")

    def test_plot_violation_rates_no_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot_violation_rates([], tmp)
            assert os.path.isfile(f"{tmp}/violation_rates.png")

    def test_plot_deadlock_frequency_no_deadlocks(self):
        clean = [r for r in self._reports if r.deadlock_count == 0]
        assert len(clean) > 0
        with tempfile.TemporaryDirectory() as tmp:
            plot_deadlock_frequency(clean, tmp)
            assert os.path.isfile(f"{tmp}/deadlock_frequency.png")

    def test_plot_pareto_frontier_single_point(self):
        reports = [self._reports[0]]
        with tempfile.TemporaryDirectory() as tmp:
            plot_pareto_frontier(reports, tmp)
            assert os.path.isfile(f"{tmp}/pareto_frontier.png")
