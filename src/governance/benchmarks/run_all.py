"""
Run all experiments and baselines, produce comparison reports.

Orchestrates the full benchmark suite: runs every scenario-strategy-seed
combination, collects metrics, and delegates to the analysis pipeline.

Real-world analogy:
    A test harness for an engine. It runs every fuel type (strategy)
    on every terrain (scenario) for multiple laps (seeds), recording
    fuel efficiency (reward), breakdowns (deadlocks), and safety
    incidents (violations).
"""

import time
from typing import Any

from ..committee.members import (
    ExampleIntegrityMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
)
from ..experiments.deadlock_maze import DeadlockMaze
from ..experiments.drift_lab import DriftLab
from ..experiments.grid_world import GridWorld
from ..experiments.metrics import ExperimentReport, generate_report
from ..experiments.temptation_bank import TemptationBank
from ..speaker import SpeakerStateMachine
from .baselines import MonolithicRL, RandomBaseline, StaticMasking, VetoOnly


def build_governance_layer() -> SpeakerStateMachine:
    """Construct a Speaker with the four standard committee members.

    Returns:
        A :class:`~..speaker.SpeakerStateMachine` with reward, safety,
        integrity, and planning members.
    """
    members = {
        "reward": ExampleRewardMember(),
        "safety": ExampleSafetyMember(),
        "integrity": ExampleIntegrityMember(),
        "planning": ExamplePlanningMember(),
    }
    return SpeakerStateMachine(
        members=members,
        default_action="emergency_shutdown",
    )


def _run_scenario(
    scenario_class, scenario_kwargs: dict, strategy_name: str, steps: int, seed: int, baseline=None
) -> ExperimentReport:
    """Run a single scenario-strategy-seed combination.

    Args:
        scenario_class: Experiment scenario class (subclass of
            :class:`~..experiments.base.ExperimentScenario`).
        scenario_kwargs: Keyword arguments for the scenario constructor.
        strategy_name: Label for this strategy (e.g. ``"governance"``).
        steps: Number of steps to run.
        seed: Random seed (for reproducibility).
        baseline: Optional :class:`BaselineGovernance` instance.
            If None, the full Speaker is used.

    Returns:
        An :class:`~..experiments.metrics.ExperimentReport`.
    """
    speaker = build_governance_layer()

    if scenario_class.__name__ == "DriftLab":
        from ..identity.core import (
            CommitmentThreshold,
            CommitmentType,
            CoreCommitment,
            EnforcementMode,
            IdentityCore,
        )

        identity = IdentityCore()
        identity.add_commitment(
            CoreCommitment(
                CommitmentType.VALUE_PRINCIPLE,
                "Always classify honestly",
                CommitmentThreshold.SUPERMAJORITY,
                EnforcementMode.INTEGRITY_VETO,
                affected_action_indices=[0],
            )
        )
        scenario = scenario_class(speaker, identity, **(scenario_kwargs or {}))
    elif scenario_class.__name__ == "DeadlockMaze":
        from ..tee.watchdog import DeadlockBreaker

        breaker = DeadlockBreaker(threshold_cycles=5)
        scenario = scenario_class(speaker, breaker, **(scenario_kwargs or {}))
    else:
        scenario = scenario_class(speaker, **(scenario_kwargs or {}))

    scenario.reset()
    step_records = []
    t0 = time.time()

    for i in range(steps):
        state = "normal"
        proposals = scenario.get_proposals(state)

        if baseline is not None:
            decision = baseline.decide(state, proposals)
            scenario.step(state, external_decision=decision)
        else:
            scenario.step(state)

        step_records.append(
            {
                "step": i,
                "reward": scenario.metrics.total_reward,
                "violations": scenario.metrics.constraint_violations,
                "deadlocks": scenario.metrics.deadlock_count,
                "runtime_ms": (time.time() - t0) * 1000 / max(1, i + 1),
            }
        )

    report = generate_report(
        f"{strategy_name}_{scenario_class.__name__}", scenario.metrics, scenario.history
    )
    report.metadata["strategy"] = strategy_name
    report.metadata["seed"] = seed
    report.metadata["step_records"] = step_records
    return report


def _get_baseline(strategy: str, seed: int):
    """Map a strategy name to a baseline instance."""
    mapping = {
        "monolithic_rl": MonolithicRL(),
        "random": RandomBaseline(seed=seed),
        "static_masking": StaticMasking(blocked_actions=frozenset()),
        "veto_only": VetoOnly(),
    }
    return mapping.get(strategy)


def _run_experiment_set(
    scenario_class,
    scenario_kwargs: dict,
    steps: int,
    seeds: int,
    strategies: list[str] | None = None,
) -> list[ExperimentReport]:
    """Run all strategy-seed combinations for a single scenario.

    Args:
        scenario_class: The scenario class.
        scenario_kwargs: Constructor kwargs for the scenario.
        steps: Steps per run.
        seeds: Number of random seeds.
        strategies: List of strategy names (default: ``["governance"]``).

    Returns:
        A list of :class:`~..experiments.metrics.ExperimentReport`.
    """
    reports = []
    if strategies is None:
        strategies = ["governance"]

    for seed in range(seeds):
        for strategy in strategies:
            baseline = _get_baseline(strategy, seed) if strategy != "governance" else None
            report = _run_scenario(
                scenario_class=scenario_class,
                scenario_kwargs=scenario_kwargs,
                strategy_name=strategy,
                steps=steps,
                seed=seed,
                baseline=baseline,
            )
            reports.append(report)
    return reports


def run_gridworld_experiments(
    steps: int = 1000, seeds: int = 1, strategies: list[str] | None = None
) -> list[ExperimentReport]:
    """Run GridWorld (poison fruit) experiments across strategies."""
    return _run_experiment_set(
        GridWorld,
        {"size": 6, "seed": 42},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
    )


def run_temptation_experiments(
    steps: int = 1000, seeds: int = 1, strategies: list[str] | None = None
) -> list[ExperimentReport]:
    """Run TemptationBank (voluntary self-binding) experiments."""
    return _run_experiment_set(
        TemptationBank,
        {},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
    )


def run_drift_experiments(
    steps: int = 1000, seeds: int = 1, strategies: list[str] | None = None
) -> list[ExperimentReport]:
    """Run DriftLab (identity drift) experiments."""
    scenario_kwargs = {}
    return _run_experiment_set(
        DriftLab,
        scenario_kwargs,
        steps=steps,
        seeds=seeds,
        strategies=strategies,
    )


def run_deadlock_experiments(
    steps: int = 1000, seeds: int = 1, strategies: list[str] | None = None
) -> list[ExperimentReport]:
    """Run DeadlockMaze (deadlock recovery) experiments."""
    return _run_experiment_set(
        DeadlockMaze,
        {},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
    )


def run_all(iterations: int = 1) -> dict[str, Any]:
    """Run all four experiments once each (legacy interface).

    Args:
        iterations: Number of times to repeat (default 1).

    Returns:
        Dict mapping experiment keys to lists of reports.
    """
    reports = {}
    for i in range(iterations):
        reports[f"gridworld_{i}"] = run_gridworld_experiments()
        reports[f"temptation_{i}"] = run_temptation_experiments()
        reports[f"drift_{i}"] = run_drift_experiments()
        reports[f"deadlock_{i}"] = run_deadlock_experiments()
    return reports


if __name__ == "__main__":
    results = run_all(iterations=1)
    for key, reps in results.items():
        print(f"\n=== {key} ===")
        for r in reps:
            print(
                f"  {r.name}: {r.total_steps} steps, "
                f"reward={r.total_reward:.1f}, "
                f"deadlocks={r.deadlock_count}, "
                f"violations={r.constraint_violations}"
            )
