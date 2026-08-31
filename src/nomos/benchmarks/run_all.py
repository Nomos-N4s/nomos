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
import warnings
from typing import Any

from ..committee.members import (
    ExampleIntegrityMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
)
from ..experiments.base import ExperimentScenario
from ..experiments.deadlock_maze import DeadlockMaze
from ..experiments.drift_lab import DriftLab
from ..experiments.grid_world import GridWorld
from ..experiments.metrics import ExperimentReport, generate_report
from ..experiments.temptation_bank import TemptationBank
from ..speaker import SpeakerStateMachine
from .baselines import MonolithicRL, RandomBaseline, StaticMasking, VetoOnly


def build_governance_layer(config_path: str | None = None) -> SpeakerStateMachine:
    """Construct a Speaker with the four standard committee members.

    Args:
        config_path: Optional path to a .parliament file. When provided,
            the Speaker is built from the DSL config instead of using
            hardcoded defaults.

    Returns:
        A :class:`~..speaker.SpeakerStateMachine` with reward, safety,
        integrity, and planning members.
    """
    if config_path:
        from ..runner import build_from_config

        return build_from_config(config_path)

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
    scenario_class,
    scenario_kwargs: dict,
    strategy_name: str,
    steps: int,
    seed: int,
    baseline=None,
    config_path: str | None = None,
) -> ExperimentReport:
    """Run a single scenario-strategy-seed combination.

    Args:
        scenario_class: Experiment scenario class (subclass of
            :class:`~..experiments.base.ExperimentScenario`).
        scenario_kwargs: Keyword arguments for the scenario constructor.
        strategy_name: Label for this strategy (e.g. ``"governance"``).
        steps: Number of steps to run.
        seed: The loop seed for this run. It reaches the scenario
            constructor when the scenario declares
            :attr:`~..experiments.base.ExperimentScenario.SEEDED`, and it
            overrides any ``seed`` in ``scenario_kwargs`` so that no caller
            can pin the whole suite to a single world. A scenario that
            declares itself deterministic is constructed without a seed and
            replays one trajectory across the loop; the seed still reaches
            the ``random`` baseline through :func:`_get_baseline`.
        baseline: Optional :class:`BaselineGovernance` instance.
            If None, the full Speaker is used.
        config_path: Optional path to a .parliament config file.

    Returns:
        An :class:`~..experiments.metrics.ExperimentReport`.

    Note:
        ``step_records[i]`` reports ``reward``, ``violations`` and
        ``deadlocks`` **at step i**, read off the
        :class:`~..experiments.base.StepResult` that
        :meth:`~..experiments.base.ExperimentScenario.step` returns. The
        running totals are separate keys: ``cumulative_reward``,
        ``cumulative_violations`` and ``cumulative_deadlocks``.

        The split is load-bearing rather than a convenience. Writing the
        running totals under the per-step names is what produced the
        bogus reward-hacking episodes of #304: the detector in
        ``analysis._detect_reward_hacking`` reads the per-step keys, and
        a monotone counter satisfies its violation gate on every step
        after the first. The reward-curve figure and the ``--csv``
        export read the cumulative keys, so both units have a name and
        neither has to be inferred.

        ``step_records[i]["runtime_ms"]`` is kept alongside the report's
        ``governance_latency_avg``; the two measure different things and
        neither replaces the other. ``runtime_ms`` is the cumulative
        wall-clock average of the whole benchmark loop up to step ``i``
        — proposal generation, the governance cycle, the environment
        transition, and this bookkeeping — and is what the ``--csv``
        export carries. ``governance_latency_avg`` covers the governance
        cycle alone.

        The two are serialised in different units: ``runtime_ms`` is
        milliseconds, ``governance_latency_avg`` is seconds. Do not read
        the raw numbers side by side — divide ``runtime_ms`` by 1000
        first. Compared in the same unit ``runtime_ms`` is still the
        larger of the two, but only by a small factor: the governance
        cycle is a large fraction of the step, not a negligible one.
    """
    speaker = build_governance_layer(config_path)
    kwargs = dict(scenario_kwargs or {})
    if scenario_class.SEEDED:
        kwargs["seed"] = seed

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
        scenario = scenario_class(speaker, identity, **kwargs)
    elif scenario_class.__name__ == "DeadlockMaze":
        from ..tee.watchdog import DeadlockBreaker

        breaker = DeadlockBreaker(threshold_cycles=5)
        scenario = scenario_class(speaker, breaker, **kwargs)
    else:
        scenario = scenario_class(speaker, **kwargs)

    scenario.reset()
    step_records = []
    t0 = time.time()

    for i in range(steps):
        state = "normal"
        proposals = scenario.get_proposals(state)

        if baseline is not None:
            decision = baseline.decide(state, proposals)
            result = scenario.step(state, external_decision=decision)
        else:
            result = scenario.step(state)

        step_records.append(
            {
                "step": i,
                "reward": result.reward,
                "violations": int(result.metrics_delta.get("constraint_violations", 0)),
                "deadlocks": int(result.decision.is_default),
                "cumulative_reward": scenario.metrics.total_reward,
                "cumulative_violations": scenario.metrics.constraint_violations,
                "cumulative_deadlocks": scenario.metrics.deadlock_count,
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


def _get_baseline(strategy: str, seed: int, scenario_class: type[ExperimentScenario]):
    """Map a strategy name to a baseline instance for one scenario.

    Args:
        strategy: Strategy name (e.g. ``"monolithic_rl"``).
        seed: Random seed, for the baselines that draw randomness.
        scenario_class: The scenario the baseline will run against.
            ``static_masking`` takes its blocklist from the scenario's
            :attr:`~..experiments.base.ExperimentScenario.STATIC_BLOCKLIST`,
            so it cannot be built without knowing the scenario.

    Returns:
        A :class:`~.baselines.BaselineGovernance`, or ``None`` when the
        strategy has no baseline (``"governance"`` or an unknown name).

    Raises:
        ValueError: If ``static_masking`` is requested for a scenario that
            declares no static blocklist, which would make the arm a
            duplicate of ``monolithic_rl``.
    """
    if strategy == "monolithic_rl":
        return MonolithicRL()
    if strategy == "random":
        return RandomBaseline(seed=seed)
    if strategy == "static_masking":
        blocked = set(scenario_class.STATIC_BLOCKLIST)
        if not blocked:
            msg = (
                f"{scenario_class.__name__} declares no STATIC_BLOCKLIST, so a "
                "static_masking arm would duplicate monolithic_rl"
            )
            raise ValueError(msg)
        return StaticMasking(blocked_actions=blocked)
    if strategy == "veto_only":
        return VetoOnly()
    return None


def _run_experiment_set(
    scenario_class,
    scenario_kwargs: dict,
    steps: int,
    seeds: int,
    strategies: list[str] | None = None,
    config_path: str | None = None,
) -> list[ExperimentReport]:
    """Run all strategy-seed combinations for a single scenario.

    Args:
        scenario_class: The scenario class.
        scenario_kwargs: Constructor kwargs for the scenario.
        steps: Steps per run.
        seeds: Number of random seeds.
        strategies: List of strategy names (default: ``["governance"]``).
        config_path: Optional path to a .parliament config file.

    Returns:
        A list of :class:`~..experiments.metrics.ExperimentReport`. The
        ``static_masking`` arm is omitted, with a :class:`RuntimeWarning`,
        for a scenario whose
        :attr:`~..experiments.base.ExperimentScenario.STATIC_BLOCKLIST` is
        empty: no fixed rule is expressible there, and running the arm anyway
        would publish ``monolithic_rl``'s numbers under a second name.
    """
    reports = []
    if strategies is None:
        strategies = ["governance"]

    for seed in range(seeds):
        for strategy in strategies:
            if strategy == "static_masking" and not scenario_class.STATIC_BLOCKLIST:
                warnings.warn(
                    f"skipping the static_masking arm on {scenario_class.__name__}: "
                    "the scenario declares no STATIC_BLOCKLIST, so the arm would "
                    "duplicate monolithic_rl",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            baseline = (
                _get_baseline(strategy, seed, scenario_class) if strategy != "governance" else None
            )
            report = _run_scenario(
                scenario_class=scenario_class,
                scenario_kwargs=scenario_kwargs,
                strategy_name=strategy,
                steps=steps,
                seed=seed,
                baseline=baseline,
                config_path=config_path,
            )
            reports.append(report)
    return reports


def run_gridworld_experiments(
    steps: int = 1000,
    seeds: int = 1,
    strategies: list[str] | None = None,
    config_path: str | None = None,
) -> list[ExperimentReport]:
    """Run GridWorld (poison fruit) experiments across strategies."""
    return _run_experiment_set(
        GridWorld,
        {"size": 6},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
        config_path=config_path,
    )


def run_temptation_experiments(
    steps: int = 1000,
    seeds: int = 1,
    strategies: list[str] | None = None,
    config_path: str | None = None,
) -> list[ExperimentReport]:
    """Run TemptationBank (voluntary self-binding) experiments."""
    return _run_experiment_set(
        TemptationBank,
        {},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
        config_path=config_path,
    )


def run_drift_experiments(
    steps: int = 1000,
    seeds: int = 1,
    strategies: list[str] | None = None,
    config_path: str | None = None,
) -> list[ExperimentReport]:
    """Run DriftLab (identity drift) experiments."""
    scenario_kwargs = {}
    return _run_experiment_set(
        DriftLab,
        scenario_kwargs,
        steps=steps,
        seeds=seeds,
        strategies=strategies,
        config_path=config_path,
    )


def run_deadlock_experiments(
    steps: int = 1000,
    seeds: int = 1,
    strategies: list[str] | None = None,
    config_path: str | None = None,
) -> list[ExperimentReport]:
    """Run DeadlockMaze (deadlock recovery) experiments."""
    return _run_experiment_set(
        DeadlockMaze,
        {},
        steps=steps,
        seeds=seeds,
        strategies=strategies,
        config_path=config_path,
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
