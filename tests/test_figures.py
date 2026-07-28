import os
import tempfile

from matplotlib.figure import Figure

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


_REPORTS = [
    _make_report("r1", 100, 2, 0, 0.0, 100, "A", "gov"),
    _make_report("r2", 80, 5, 1, 0.01, 100, "A", "mono"),
    _make_report("r3", 150, 0, 0, 0.0, 100, "B", "gov"),
    _make_report("r4", 60, 8, 2, 0.02, 100, "B", "mono"),
    _make_report("r5", 90, 3, 0, 0.0, 100, "A", "rand"),
    _make_report("r6", 110, 1, 0, 0.0, 100, "B", "rand"),
]


# -- _ci_to_error --


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


# -- plot_reward_curves --


def test_reward_curves_returns_figure():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_reward_curves(_REPORTS, tmp)
        assert isinstance(fig, Figure)


def test_reward_curves_2x2_layout():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_reward_curves(_REPORTS, tmp)
        assert len(fig.axes) == 4


def test_reward_curves_legend_has_strategies():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_reward_curves(_REPORTS, tmp)
        legend_texts = []
        for ax in fig.axes:
            leg = ax.get_legend()
            if leg is not None:
                legend_texts.extend(t.get_text() for t in leg.get_texts())
        assert "gov" in legend_texts
        assert "mono" in legend_texts
        assert "rand" in legend_texts


def test_reward_curves_saves_files():
    with tempfile.TemporaryDirectory() as tmp:
        plot_reward_curves(_REPORTS, tmp)
        assert os.path.isfile(f"{tmp}/reward_curves.png")
        assert os.path.isfile(f"{tmp}/reward_curves.svg")


def test_reward_curves_single_strategy():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_reward_curves([_REPORTS[0]], tmp)
        assert isinstance(fig, Figure)


# -- plot_violation_rates --


def test_violation_rates_returns_figure():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_violation_rates(_REPORTS, tmp)
        assert isinstance(fig, Figure)


def test_violation_rates_legend_has_strategies():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_violation_rates(_REPORTS, tmp)
        ax = fig.axes[0]
        legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "gov" in legend_labels
        assert "mono" in legend_labels
        assert "rand" in legend_labels


def test_violation_rates_error_bars_present():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_violation_rates(_REPORTS, tmp)
        ax = fig.axes[0]
        containers = [c for c in ax.containers if hasattr(c, "datavalues")]
        assert len(containers) == len(set(r.metadata.get("strategy", "unknown") for r in _REPORTS))


def test_violation_rates_saves_files():
    with tempfile.TemporaryDirectory() as tmp:
        plot_violation_rates(_REPORTS, tmp)
        assert os.path.isfile(f"{tmp}/violation_rates.png")
        assert os.path.isfile(f"{tmp}/violation_rates.svg")


def test_violation_rates_no_reports():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_violation_rates([], tmp)
        assert isinstance(fig, Figure)


# -- plot_deadlock_frequency --


def test_deadlock_frequency_returns_figure():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_deadlock_frequency(_REPORTS, tmp)
        assert isinstance(fig, Figure)


def test_deadlock_frequency_legend_has_strategies():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_deadlock_frequency(_REPORTS, tmp)
        ax = fig.axes[0]
        legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "gov" in legend_labels
        assert "mono" in legend_labels


def test_deadlock_frequency_saves_files():
    with tempfile.TemporaryDirectory() as tmp:
        plot_deadlock_frequency(_REPORTS, tmp)
        assert os.path.isfile(f"{tmp}/deadlock_frequency.png")
        assert os.path.isfile(f"{tmp}/deadlock_frequency.svg")


def test_deadlock_frequency_no_deadlocks():
    clean = [r for r in _REPORTS if r.deadlock_count == 0]
    assert len(clean) > 0
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_deadlock_frequency(clean, tmp)
        assert isinstance(fig, Figure)


# -- plot_pareto_frontier --


def test_pareto_frontier_returns_figure():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_pareto_frontier(_REPORTS, tmp)
        assert isinstance(fig, Figure)


def test_pareto_frontier_at_least_two_strategies():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_pareto_frontier(_REPORTS, tmp)
        ax = fig.axes[0]
        assert len(ax.get_legend().get_texts()) >= 2


def test_pareto_frontier_saves_files():
    with tempfile.TemporaryDirectory() as tmp:
        plot_pareto_frontier(_REPORTS, tmp)
        assert os.path.isfile(f"{tmp}/pareto_frontier.png")
        assert os.path.isfile(f"{tmp}/pareto_frontier.svg")


def test_pareto_frontier_single_point():
    with tempfile.TemporaryDirectory() as tmp:
        fig = plot_pareto_frontier([_REPORTS[0]], tmp)
        assert isinstance(fig, Figure)


# -- generate_all_figures --


def test_generate_all_figures_returns_dict():
    with tempfile.TemporaryDirectory() as tmp:
        figs = generate_all_figures(_REPORTS, tmp)
        expected_keys = {"reward_curves", "violation_rates", "deadlock_frequency", "pareto_frontier"}
        assert figs.keys() == expected_keys


def test_generate_all_figures_all_figure_types():
    with tempfile.TemporaryDirectory() as tmp:
        figs = generate_all_figures(_REPORTS, tmp)
        for f in figs.values():
            assert isinstance(f, Figure)


def test_generate_all_figures_saves_all_files():
    with tempfile.TemporaryDirectory() as tmp:
        generate_all_figures(_REPORTS, tmp)
        for name in ["reward_curves", "violation_rates", "deadlock_frequency", "pareto_frontier"]:
            assert os.path.isfile(f"{tmp}/{name}.png")
            assert os.path.isfile(f"{tmp}/{name}.svg")



