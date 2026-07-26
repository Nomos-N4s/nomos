"""
run_all.py — Run all experiments and baselines, produce comparison report.
"""

import time
from typing import Any, Dict, List, Optional

from ..committee.members import (
    ExampleRewardMember, ExampleSafetyMember, ExampleIntegrityMember,
    ExamplePlanningMember,
)
from ..speaker import SpeakerStateMachine
from ..experiments.grid_world import GridWorld
from ..experiments.temptation_bank import TemptationBank
from ..experiments.drift_lab import DriftLab
from ..experiments.deadlock_maze import DeadlockMaze
from ..experiments.metrics import generate_report, ExperimentReport
from ..tee.watchdog import DeadlockBreaker
from ..identity.core import IdentityCore, CoreCommitment, CommitmentType, CommitmentThreshold, EnforcementMode
from .baselines import MonolithicRL, RandomBaseline, StaticMasking, VetoOnly, BaselineGovernance


def build_governance_layer():
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


def _run_scenario(scenario_class, scenario_kwargs: dict,
                  strategy_name: str,
                  steps: int, seed: int, baseline=None) -> ExperimentReport:
    speaker = build_governance_layer()

    if scenario_class.__name__ == "DriftLab":
        from ..identity.core import IdentityCore, CoreCommitment, CommitmentType, CommitmentThreshold, EnforcementMode
        identity = IdentityCore()
        identity.add_commitment(CoreCommitment(
            CommitmentType.VALUE_PRINCIPLE,
            "Always classify honestly",
            CommitmentThreshold.SUPERMAJORITY,
            EnforcementMode.INTEGRITY_VETO,
            affected_action_indices=[0],
        ))
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

        step_records.append({
            "step": i,
            "reward": scenario.metrics.total_reward,
            "violations": scenario.metrics.constraint_violations,
            "deadlocks": scenario.metrics.deadlock_count,
            "runtime_ms": (time.time() - t0) * 1000 / max(1, i + 1),
        })

    report = generate_report(f"{strategy_name}_{scenario_class.__name__}",
                              scenario.metrics, scenario.history)
    report.metadata["strategy"] = strategy_name
    report.metadata["seed"] = seed
    report.metadata["step_records"] = step_records
    return report


def _get_baseline(strategy: str, seed: int):
    mapping = {
        "monolithic_rl": MonolithicRL(),
        "random": RandomBaseline(seed=seed),
        "static_masking": StaticMasking(blocked_actions=frozenset()),
        "veto_only": VetoOnly(),
    }
    return mapping.get(strategy)


def _run_experiment_set(scenario_class, scenario_kwargs: dict,
                         steps: int, seeds: int,
                         strategies: Optional[List[str]] = None) -> List[ExperimentReport]:
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


def run_gridworld_experiments(steps: int = 1000, seeds: int = 1,
                               strategies: Optional[List[str]] = None) -> List[ExperimentReport]:
    return _run_experiment_set(
        GridWorld, {"size": 6, "seed": 42},
        steps=steps, seeds=seeds, strategies=strategies,
    )


def run_temptation_experiments(steps: int = 1000, seeds: int = 1,
                                strategies: Optional[List[str]] = None) -> List[ExperimentReport]:
    return _run_experiment_set(
        TemptationBank, {},
        steps=steps, seeds=seeds, strategies=strategies,
    )


def run_drift_experiments(steps: int = 1000, seeds: int = 1,
                           strategies: Optional[List[str]] = None) -> List[ExperimentReport]:
    scenario_kwargs = {}
    return _run_experiment_set(
        DriftLab, scenario_kwargs,
        steps=steps, seeds=seeds, strategies=strategies,
    )


def run_deadlock_experiments(steps: int = 1000, seeds: int = 1,
                              strategies: Optional[List[str]] = None) -> List[ExperimentReport]:
    return _run_experiment_set(
        DeadlockMaze, {},
        steps=steps, seeds=seeds, strategies=strategies,
    )


def run_all(iterations: int = 1) -> Dict[str, Any]:
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
            print(f"  {r.name}: {r.total_steps} steps, "
                  f"reward={r.total_reward:.1f}, "
                  f"deadlocks={r.deadlock_count}, "
                  f"violations={r.constraint_violations}")
