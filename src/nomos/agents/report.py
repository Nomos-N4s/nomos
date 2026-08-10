"""
Report generation for agent validation runs.

Writes three artifacts to ``results/agent/``:

- ``agent_benchmark_results.json`` — full per-pair and aggregate metrics
- ``agent_benchmark_summary.csv`` — one row per seed pair
- ``agent_report.md`` — human-readable markdown summary

Export conventions (CSV columns, JSON layout, rounding) mirror
:mod:`~..benchmarks.analysis`, so agent runs and RL benchmark runs stay
comparable side by side.

Real-world analogy:
    A clinical trial's study report: the raw data tables (CSV), the
    full dataset for auditors (JSON), and the plain-language summary
    for the board (markdown).
"""

import csv
import json
import os
from dataclasses import asdict
from typing import Any

from .harness import PairResult
from .metrics import (
    AgentPairMetrics,
    AgentSummary,
    JudgeAlignmentMetrics,
    JudgeAssessment,
    compute_pair_metrics,
    judge_alignment,
    summarize_pairs,
)

#: Default output directory for agent validation artifacts.
AGENT_REPORT_DIR = "results/agent"

_SUMMARY_CSV_COLUMNS = [
    "seed",
    "num_steps",
    "ungoverned_violation_rate",
    "governed_violation_rate",
    "reward_preservation_ratio",
    "veto_precision",
    "veto_recall",
]


def _round(value: float | None, ndigits: int = 4) -> float | str:
    """Round a metric for export; ``""`` for missing values."""
    if value is None:
        return ""
    return round(value, ndigits)


def format_agent_summary(summary: AgentSummary) -> str:
    """Format the aggregate summary as a compact text block.

    Args:
        summary: The aggregated :class:`AgentSummary`.

    Returns:
        A multi-line string suitable for terminal output.
    """
    lines = [
        f"Agent validation: {summary.num_pairs} pairs, {summary.num_steps} steps",
        f"  Violation rate (ungoverned): {summary.ungoverned_violation_rate:.4f}",
        f"  Violation rate (governed):   {summary.governed_violation_rate:.4f}",
        f"  Pairs governed <= ungoverned: {summary.governed_rate_never_worse:.1%}",
        f"  Reward preservation: {summary.reward_preservation_ratio:.4f}",
        f"    CI: [{summary.reward_preservation_ci[0]:.4f}, "
        f"{summary.reward_preservation_ci[1]:.4f}]",
        f"    Cohen's d: {summary.reward_cohens_d:+.3f}",
        f"  Veto precision: {summary.veto_precision:.4f}",
        f"  Veto recall:    {summary.veto_recall:.4f}",
        f"  Latency p50 (gov/ungov): {summary.latency_p50['governed']:.4f}s / "
        f"{summary.latency_p50['ungoverned']:.4f}s",
        f"  Latency p95 (gov/ungov): {summary.latency_p95['governed']:.4f}s / "
        f"{summary.latency_p95['ungoverned']:.4f}s",
    ]
    return "\n".join(lines)


def write_agent_report_markdown(
    summary: AgentSummary,
    path: str,
    judge: JudgeAlignmentMetrics | None = None,
) -> str:
    """Write the human-readable markdown report.

    Args:
        summary: The aggregated :class:`AgentSummary`.
        path: File path for the markdown output.
        judge: Optional judge alignment metrics; included when given.

    Returns:
        The markdown text that was written.
    """
    steps_per_pair = summary.num_steps // max(summary.num_pairs, 1)
    md = [
        "# Agent Validation Report",
        "",
        "## Overview",
        f"- Seed pairs: {summary.num_pairs}",
        f"- Steps per pair: {steps_per_pair}",
        f"- Total steps: {summary.num_steps}",
        "",
        "## Violation rates",
        f"- Ungoverned arm (counterfactual oracle): {summary.ungoverned_violation_rate:.4f}",
        f"- Governed arm (actual): {summary.governed_violation_rate:.4f}",
        f"- Pairs where governed rate <= ungoverned rate: {summary.governed_rate_never_worse:.0%}",
        "",
        "## Reward preservation",
        f"- Mean ratio (governed / ungoverned): {summary.reward_preservation_ratio:.4f}",
        f"- Bootstrap 95% CI: [{summary.reward_preservation_ci[0]:.4f}, "
        f"{summary.reward_preservation_ci[1]:.4f}]",
        f"- Cohen's d (governed vs ungoverned reward): {summary.reward_cohens_d:+.3f}",
        "",
        "## Veto precision and recall",
        f"- Precision: {summary.veto_precision:.4f}",
        f"- Recall: {summary.veto_recall:.4f}",
        "",
        "## Backend latency",
        f"- p50 governed: {summary.latency_p50['governed']:.4f}s | "
        f"p50 ungoverned: {summary.latency_p50['ungoverned']:.4f}s",
        f"- p95 governed: {summary.latency_p95['governed']:.4f}s | "
        f"p95 ungoverned: {summary.latency_p95['ungoverned']:.4f}s",
    ]
    if judge is not None:
        md += [
            "",
            "## LLM-as-judge alignment",
            f"- Samples judged: {judge.num_samples}",
            f"- Mean score (1-5): {judge.mean_score:.2f}",
            f"- Oracle agreement: {judge.oracle_agreement:.1%}",
            f"- Inter-rater agreement: {judge.inter_rater_agreement:.1%}",
            f"- Mean absolute score difference: {judge.mean_abs_score_diff:.2f}",
        ]
    md.append("")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return "\n".join(md)


def export_agent_summary_csv(pair_metrics: list[AgentPairMetrics], path: str) -> None:
    """Export one row per seed pair to a CSV file.

    Args:
        pair_metrics: Per-pair metrics.
        path: File path for the CSV output.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_SUMMARY_CSV_COLUMNS)
        for m in pair_metrics:
            w.writerow(
                [
                    m.seed,
                    m.num_steps,
                    _round(m.ungoverned_violation_rate),
                    _round(m.governed_violation_rate),
                    _round(m.reward_preservation_ratio),
                    _round(m.veto_precision),
                    _round(m.veto_recall),
                ]
            )


def export_agent_results_json(
    pair_metrics: list[AgentPairMetrics],
    summary: AgentSummary,
    path: str,
    judge: JudgeAlignmentMetrics | None = None,
) -> None:
    """Export all agent metrics to a single JSON file.

    Args:
        pair_metrics: Per-pair metrics.
        summary: The aggregated :class:`AgentSummary`.
        path: File path for JSON output.
        judge: Optional judge alignment metrics.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {
        "num_pairs": summary.num_pairs,
        "num_steps": summary.num_steps,
        "summary": {
            "ungoverned_violation_rate": round(summary.ungoverned_violation_rate, 4),
            "governed_violation_rate": round(summary.governed_violation_rate, 4),
            "governed_rate_never_worse": round(summary.governed_rate_never_worse, 4),
            "reward_preservation_ratio": round(summary.reward_preservation_ratio, 4),
            "reward_preservation_ci": [
                round(summary.reward_preservation_ci[0], 4),
                round(summary.reward_preservation_ci[1], 4),
            ],
            "reward_cohens_d": round(summary.reward_cohens_d, 4),
            "veto_precision": round(summary.veto_precision, 4),
            "veto_recall": round(summary.veto_recall, 4),
            "latency_p50": {k: round(v, 6) for k, v in summary.latency_p50.items()},
            "latency_p95": {k: round(v, 6) for k, v in summary.latency_p95.items()},
        },
        "pairs": [asdict(m) for m in pair_metrics],
        "judge": asdict(judge) if judge is not None else None,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_agent_analysis(
    pairs: list[PairResult],
    assessments: list[JudgeAssessment] | None = None,
    output_dir: str = AGENT_REPORT_DIR,
) -> dict[str, Any]:
    """Run the full agent validation analysis and write all artifacts.

    Args:
        pairs: All governed/ungoverned pairs (one per seed).
        assessments: Optional LLM-as-judge assessments to aggregate.
        output_dir: Output directory (default ``results/agent``).

    Returns:
        Dict with keys ``summary``, ``pair_metrics``, ``judge``,
        ``summary_csv``, ``results_json``, ``report_md``.
    """
    summary = summarize_pairs(pairs)
    pair_metrics = [compute_pair_metrics(p) for p in pairs]
    judge = judge_alignment(assessments) if assessments else None

    summary_csv = os.path.join(output_dir, "agent_benchmark_summary.csv")
    results_json = os.path.join(output_dir, "agent_benchmark_results.json")
    report_md = os.path.join(output_dir, "agent_report.md")

    export_agent_summary_csv(pair_metrics, summary_csv)
    export_agent_results_json(pair_metrics, summary, results_json, judge)
    write_agent_report_markdown(summary, report_md, judge)

    return {
        "summary": summary,
        "pair_metrics": pair_metrics,
        "judge": judge,
        "summary_csv": summary_csv,
        "results_json": results_json,
        "report_md": report_md,
    }
