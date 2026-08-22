import csv
import io
import os
import sys
import tempfile

import pytest

from src.nomos.experiments.metrics import ExperimentReport
from src.nomos.runner import (
    _build_baseline_flags,
    _export_csv,
    _resolve_csv_path,
    _run_all_scenarios,
    cmd_speaker,
    main,
)


class TestResolveCsvPath:
    def test_none_returns_none(self):
        assert _resolve_csv_path(None) is None

    def test_empty_string_generates_timestamp(self):
        path = _resolve_csv_path("")
        assert path.startswith("results/run_")
        assert path.endswith(".csv")

    def test_custom_path_returned_as_is(self):
        assert _resolve_csv_path("my/path.csv") == "my/path.csv"


def _csv_report():
    """A report whose step records are shaped the way the runner writes them.

    Two steps, each earning 5.0, the second one violating — so the
    per-step columns and the running totals cannot be confused (#304).
    """
    return ExperimentReport(
        name="test", total_steps=2, total_reward=10.0, avg_reward_per_step=5.0,
        deadlock_count=0, deadlock_rate=0.0, constraint_violations=1, veto_count=0,
        final_identity_drift=0.0, governance_latency_avg=0.0,
        metadata={"scenario": "GridWorld", "strategy": "governance", "seed": 0,
                  "step_records": [
                      {"step": 0, "reward": 5.0, "violations": 0, "deadlocks": 0,
                       "cumulative_reward": 5.0, "cumulative_violations": 0,
                       "cumulative_deadlocks": 0, "runtime_ms": 1.0},
                      {"step": 1, "reward": 5.0, "violations": 1, "deadlocks": 0,
                       "cumulative_reward": 10.0, "cumulative_violations": 1,
                       "cumulative_deadlocks": 0, "runtime_ms": 1.0},
                  ]},
    )


class TestExportCsv:
    def test_creates_csv_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            _export_csv([_csv_report()], path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "timestamp" in content
            assert "GridWorld" in content

    def test_per_step_and_cumulative_columns_are_both_carried(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            _export_csv([_csv_report()], path)
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
        assert [r["reward"] for r in rows] == ["5.0", "5.0"]
        assert [r["cumulative_reward"] for r in rows] == ["5.0", "10.0"]
        assert [r["violations"] for r in rows] == ["0", "1"]
        assert [r["cumulative_violations"] for r in rows] == ["0", "1"]


class TestBuildBaselineFlags:
    def test_default_flags(self):
        class Args:
            steps = 100
            seeds = 5
            baselines = False
            strategies = None
        flags = _build_baseline_flags(Args())
        assert flags["steps"] == 100
        assert flags["seeds"] == 5
        assert "strategies" not in flags

    def test_baselines_without_strategies_uses_all(self):
        class Args:
            steps = 100
            seeds = 1
            baselines = True
            strategies = None
        flags = _build_baseline_flags(Args())
        assert "strategies" in flags
        assert len(flags["strategies"]) == 5

    def test_baselines_with_custom_strategies(self):
        class Args:
            steps = 100
            seeds = 1
            baselines = True
            strategies = "governance,random"
        flags = _build_baseline_flags(Args())
        assert flags["strategies"] == ["governance", "random"]


class TestRunAllScenarios:
    def test_returns_reports_from_all_scenarios(self):
        flags = {"steps": 2, "seeds": 1}
        reports = _run_all_scenarios(flags)
        assert len(reports) == 4
        scenarios = set(r.metadata.get("scenario") for r in reports)
        assert scenarios == {"GridWorld", "TemptationBank", "DriftLab", "DeadlockMaze"}


class TestCmdSpeaker:
    def test_runs_without_error(self):
        class Args:
            pass
        try:
            cmd_speaker(Args())
        except Exception as e:
            pytest.fail(f"cmd_speaker raised: {e}")


class TestMain:
    def test_main_speaker(self):
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "speaker"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

    def test_main_gridworld(self):
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "gridworld", "--steps", "2", "--seeds", "1"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

    def test_main_temptation(self):
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "temptation", "--steps", "2", "--seeds", "1"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

    def test_main_no_command_prints_help(self):
        captured = io.StringIO()
        sys.stdout = captured
        old_argv = sys.argv
        try:
            sys.argv = ["runner"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            sys.stdout = sys.__stdout__

    def test_main_prove(self):
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "prove", "--all"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

    def test_main_adversary_help(self):
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "adversary", "--help"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
