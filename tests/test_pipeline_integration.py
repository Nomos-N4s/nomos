"""
End-to-end pipeline integration test.

Runs a mini benchmark (2 scenarios x 2 strategies x 2 seeds x 10 steps)
and exercises experiment -> benchmark -> analysis -> figures -> export.
"""

import csv
import json
import os
import tempfile

import pytest

from src.governance.benchmarks.analysis import (
    export_results_json,
    export_summary_csv,
    run_analysis,
)
from src.governance.benchmarks.figures import generate_all_figures
from src.governance.benchmarks.run_all import (
    run_gridworld_experiments,
    run_temptation_experiments,
)

_STRATEGIES = ["governance", "random"]
_STEPS = 10
_SEEDS = 2


@pytest.mark.slow
class TestFullPipeline:
    """Integration test: experiment --> benchmark --> analysis --> figures --> export."""

    def _run_mini_benchmark(self):
        reports = []
        for runner, scenario in [
            (run_gridworld_experiments, "GridWorld"),
            (run_temptation_experiments, "TemptationBank"),
        ]:
            reps = runner(steps=_STEPS, seeds=_SEEDS, strategies=_STRATEGIES)
            for r in reps:
                r.metadata["scenario"] = scenario
            reports.extend(reps)
        assert len(reports) == 2 * len(_STRATEGIES) * _SEEDS
        return reports

    def test_analysis_aggregates(self):
        """run_analysis() produces non-empty aggregates with expected structure."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        aggregates = result["aggregates"]
        assert len(aggregates) > 0
        for a in aggregates:
            assert a.strategy in _STRATEGIES
            assert a.scenario in ("GridWorld", "TemptationBank")
            assert a.num_seeds == _SEEDS
            assert a.mean_reward is not None

    def test_analysis_effect_sizes(self):
        """Effect sizes include at least one non-zero Cohen's d."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        effect_sizes = result["effect_sizes"]
        assert len(effect_sizes) > 0
        nonzero_d = [e for e in effect_sizes if e["cohens_d"] != 0.0]
        assert len(nonzero_d) > 0
        for es in effect_sizes:
            assert "p_value_corrected" in es
            assert "p_value_holm" in es
            assert "significant" in es

    def test_analysis_hacking_detection(self):
        """Hacking detection runs without error."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        assert isinstance(result["hacking_episodes"], list)

    def test_figures_return_four_figures(self):
        """generate_all_figures() returns a dict of 4 Figure objects."""
        reports = self._run_mini_benchmark()
        with tempfile.TemporaryDirectory() as tmp:
            figs = generate_all_figures(reports, tmp)
            assert isinstance(figs, dict)
            assert figs.keys() == {"reward_curves", "violation_rates", "deadlock_frequency", "pareto_frontier"}
            from matplotlib.figure import Figure
            for name, fig in figs.items():
                assert isinstance(fig, Figure), f"{name} is not a Figure"

    def test_export_csv(self):
        """CSV export produces a parseable, non-empty file."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "summary.csv")
            export_summary_csv(result["aggregates"], path)
            assert os.path.isfile(path)
            with open(path, newline="") as f:
                reader = list(csv.reader(f))
            assert len(reader) > 1
            header = reader[0]
            assert "strategy" in header
            assert "mean_reward" in header

    def test_export_json(self):
        """JSON export produces a file with expected keys."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            export_results_json(
                reports,
                result["aggregates"],
                result["effect_sizes"],
                result["hacking_episodes"],
                path,
            )
            assert os.path.isfile(path)
            with open(path) as f:
                data = json.load(f)
            assert "aggregates" in data
            assert "effect_sizes" in data
            assert "reward_hacking_episodes" in data
            assert "num_reports" in data
            assert data["num_reports"] == len(reports)

    def test_pipeline_analysis_no_errors(self):
        """Full pipeline runs without exceptions."""
        reports = self._run_mini_benchmark()
        result = run_analysis(reports)
        assert "aggregates" in result
        assert "effect_sizes" in result
        assert "hacking_episodes" in result
        assert "summary_csv" in result
        assert "results_json" in result
