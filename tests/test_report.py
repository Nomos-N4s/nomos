import io
import sys

from src.nomos.benchmarks.report import format_comparison, format_report, print_all_reports
from src.nomos.experiments.metrics import ExperimentReport


def _make_report(name="test", reward=100.0, steps=100, deadlocks=0, violations=0, drift=0.0):
    return ExperimentReport(
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
        metadata={},
    )


class TestFormatReport:
    def test_basic_fields(self):
        report = _make_report(name="GridWorld", reward=150.0, steps=50, deadlocks=2, violations=1, drift=0.05)
        output = format_report(report)
        assert "GridWorld" in output
        assert "50" in output
        assert "150.00" in output
        assert "2" in output
        assert "1" in output
        assert "0.0500" in output

    def test_multiline_string(self):
        report = _make_report(name="Test")
        output = format_report(report)
        lines = output.strip().split("\n")
        assert len(lines) >= 6
        assert lines[0].startswith("Experiment:")

    def test_deadlock_rate_percentage(self):
        report = _make_report(deadlocks=25, steps=100)
        output = format_report(report)
        assert "25.0%" in output


class TestFormatComparison:
    def test_baseline_name_appears(self):
        comparisons = {
            "monolithic_rl": {"reward_diff": -20.0, "violations_diff": 5},
            "random": {"reward_diff": -50.0},
        }
        output = format_comparison("governance", comparisons)
        assert "governance" in output
        assert "monolithic_rl" in output
        assert "random" in output
        assert "-20" in output

    def test_positive_diff_shows_plus(self):
        comparisons = {"random": {"reward_diff": 10.0}}
        output = format_comparison("baseline", comparisons)
        assert "+10" in output

    def test_negative_diff_no_plus(self):
        comparisons = {"random": {"reward_diff": -10.0}}
        output = format_comparison("baseline", comparisons)
        assert "-10" in output


class TestPrintAllReports:
    def test_single_report_prints(self):
        report = _make_report(name="Single")
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_all_reports([report])
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "Single" in output

    def test_multiple_reports_triggers_comparison(self):
        r1 = _make_report(name="gov", reward=100.0)
        r2 = _make_report(name="random", reward=50.0)
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_all_reports([r1, r2])
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "gov" in output
        assert "random" in output
        assert "Comparison" in output or "comparison" in output

    def test_empty_list(self):
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_all_reports([])
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert output == "" or output.strip() == ""
