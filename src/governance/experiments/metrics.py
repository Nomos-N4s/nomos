"""
Collectors and reporters for experiment results.

Provides data structures and utility functions for generating
:class:`ExperimentReport` instances and comparing results across
different strategies and seeds.

Real-world analogy:
    A lab notebook that records each experiment's conditions (strategy,
    seed, steps) and results (reward, violations, deadlocks), making it
    easy to compare which experimental conditions produced the best outcomes.
"""

import json
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExperimentReport:
    """A summary report for a single experiment run.

    Attributes:
        name: Experiment name (e.g. ``"GridWorld-FullGovernance"``).
        total_steps: Number of steps executed.
        total_reward: Cumulative raw reward.
        avg_reward_per_step: Mean reward per step.
        deadlock_count: Number of default (no-decision) outcomes.
        deadlock_rate: Fraction of steps that resulted in deadlock.
        constraint_violations: Number of governed constraints broken.
        veto_count: Total vetoes applied across all steps.
        final_identity_drift: Cosine distance of identity vector from
            its genesis state at the final step.
        governance_latency_avg: Mean governance cycle duration (seconds).
        metadata: Arbitrary key-value data (e.g. seed, strategy args).
    """

    name: str
    total_steps: int
    total_reward: float
    avg_reward_per_step: float
    deadlock_count: int
    deadlock_rate: float
    constraint_violations: int
    veto_count: int
    final_identity_drift: float
    governance_latency_avg: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict for JSON serialisation."""
        return asdict(self)

    def to_json(self) -> str:
        """Pretty-printed JSON string of this report."""
        return json.dumps(self.to_dict(), indent=2)


def generate_report(name: str, metrics, history) -> ExperimentReport:
    """Build an :class:`ExperimentReport` from metrics and step history.

    Args:
        name: A human-readable label for this run.
        metrics: An :class:`~.base.ExperimentMetrics` instance.
        history: List of :class:`~.base.StepResult` tuples.

    Returns:
        A populated :class:`ExperimentReport`.
    """
    steps = metrics.total_steps
    return ExperimentReport(
        name=name,
        total_steps=steps,
        total_reward=metrics.total_reward,
        avg_reward_per_step=metrics.total_reward / max(steps, 1),
        deadlock_count=metrics.deadlock_count,
        deadlock_rate=metrics.deadlock_count / max(steps, 1),
        constraint_violations=metrics.constraint_violations,
        veto_count=metrics.veto_count,
        final_identity_drift=metrics.identity_drift[-1] if metrics.identity_drift else 0.0,
        governance_latency_avg=statistics.mean(metrics.governance_latencies)
        if metrics.governance_latencies
        else 0.0,
    )


def compare_reports(reports: list[ExperimentReport]) -> dict[str, Any]:
    """Compare multiple reports against the first (baseline).

    Computes percentage changes in reward, absolute changes in deadlock
    rate, and raw violations differences.

    Args:
        reports: List of reports, where ``reports[0]`` is the baseline.

    Returns:
        A dict with keys ``"baseline"`` and one entry per comparison report.
    """
    baseline = reports[0]
    comparison = {"baseline": baseline.name}
    for r in reports[1:]:
        improvement = {}
        if baseline.avg_reward_per_step > 0:
            improvement["reward_change"] = round(
                (r.avg_reward_per_step - baseline.avg_reward_per_step)
                / baseline.avg_reward_per_step
                * 100,
                1,
            )
        improvement["deadlock_rate_change"] = round(
            (r.deadlock_rate - baseline.deadlock_rate) * 100, 2
        )
        improvement["violations_change"] = r.constraint_violations - baseline.constraint_violations
        comparison[r.name] = improvement
    return comparison
