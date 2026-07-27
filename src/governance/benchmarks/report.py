"""
Human-readable comparison report from experiment metrics.

Formats :class:`~..experiments.metrics.ExperimentReport` instances and
comparison results for terminal output.

Real-world analogy:
    A race results sheet: each driver (strategy) gets a row with their
    finishing time (reward), DNF count (deadlocks), and penalty points
    (violations).
"""

from typing import Any, Dict, List

from ..experiments.metrics import ExperimentReport, compare_reports


def format_report(report: ExperimentReport) -> str:
    """Format a single experiment report as a human-readable string.

    Args:
        report: The :class:`~..experiments.metrics.ExperimentReport` to format.

    Returns:
        A multi-line string suitable for terminal output.
    """
    lines = [
        f"Experiment: {report.name}",
        f"  Steps:        {report.total_steps}",
        f"  Total reward: {report.total_reward:.2f}",
        f"  Avg reward:   {report.avg_reward_per_step:.3f}",
        f"  Deadlocks:    {report.deadlock_count} ({report.deadlock_rate:.1%})",
        f"  Violations:   {report.constraint_violations}",
        f"  Vetoes:       {report.veto_count}",
        f"  Identity drift: {report.final_identity_drift:.4f}",
    ]
    return "\n".join(lines)


def format_comparison(baseline_name: str, comparisons: Dict[str, Any]) -> str:
    """Format strategy comparisons against a baseline.

    Args:
        baseline_name: The baseline strategy name.
        comparisons: Dict mapping comparison strategy names to
            their metric diffs (from :func:`~..experiments.metrics.compare_reports`).

    Returns:
        A multi-line string showing deltas.
    """
    lines = [f"Comparison vs {baseline_name}:"]
    for name, metrics in comparisons.items():
        lines.append(f"  {name}:")
        for k, v in metrics.items():
            sign = "+" if isinstance(v, (int, float)) and v > 0 else ""
            lines.append(f"    {k}: {sign}{v}")
    return "\n".join(lines)


def print_all_reports(reports: List[ExperimentReport]):
    """Print all reports to stdout with an optional comparison section.

    Args:
        reports: List of reports (first is baseline for comparison).
    """
    for r in reports:
        print(format_report(r))
        print()
    if len(reports) > 1:
        comparison = compare_reports(reports)
        if len(comparison) > 1:
            print(format_comparison(reports[0].name, {
                k: v for k, v in comparison.items() if k != "baseline"
            }))
