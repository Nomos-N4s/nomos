import inspect

import pytest

from src.nomos.benchmarks.baselines import (
    MonolithicRL,
    RandomBaseline,
    StaticMasking,
    VetoOnly,
)
from src.nomos.benchmarks.run_all import (
    _get_baseline,
    _run_experiment_set,
    _run_scenario,
    build_governance_layer,
    run_all,
    run_deadlock_experiments,
    run_drift_experiments,
    run_gridworld_experiments,
    run_temptation_experiments,
)
from src.nomos.experiments.deadlock_maze import DeadlockMaze
from src.nomos.experiments.drift_lab import DriftLab
from src.nomos.experiments.grid_world import GridWorld
from src.nomos.experiments.temptation_bank import TemptationBank
from src.nomos.identity.core import IdentityCore
from src.nomos.runner import ALL_STRATEGIES
from src.nomos.tee.watchdog import DeadlockBreaker


class TestBuildGovernanceLayer:
    def test_returns_speaker(self):
        speaker = build_governance_layer()
        assert speaker is not None
        assert "reward" in speaker.members
        assert "safety" in speaker.members
        assert "integrity" in speaker.members
        assert "planning" in speaker.members
        assert speaker.default_action == "emergency_shutdown"


class TestGetBaseline:
    def test_governance_returns_none(self):
        assert _get_baseline("governance", 0, GridWorld) is None

    def test_monolithic_rl(self):
        bl = _get_baseline("monolithic_rl", 0, GridWorld)
        assert isinstance(bl, MonolithicRL)

    def test_random(self):
        bl = _get_baseline("random", 0, GridWorld)
        assert isinstance(bl, RandomBaseline)

    def test_static_masking(self):
        bl = _get_baseline("static_masking", 0, TemptationBank)
        assert isinstance(bl, StaticMasking)

    def test_veto_only(self):
        bl = _get_baseline("veto_only", 0, GridWorld)
        assert isinstance(bl, VetoOnly)

    def test_unknown_returns_none(self):
        assert _get_baseline("unknown", 0, GridWorld) is None


class TestStaticMaskingBlocklist:
    def test_blocklist_comes_from_the_scenario(self):
        for scenario_class in (TemptationBank, DriftLab, DeadlockMaze):
            bl = _get_baseline("static_masking", 0, scenario_class)
            assert bl.blocked == set(scenario_class.STATIC_BLOCKLIST)
            assert bl.blocked

    def test_blocklist_matches_actions_the_scenario_emits(self):
        speaker = build_governance_layer()
        scenarios = [
            TemptationBank(speaker),
            DriftLab(speaker, IdentityCore()),
            DeadlockMaze(speaker, DeadlockBreaker(threshold_cycles=5)),
        ]
        for scenario in scenarios:
            scenario.reset()
            emitted = {p.action for p in scenario.get_proposals("normal")}
            assert emitted >= type(scenario).STATIC_BLOCKLIST

    def test_scenario_without_a_blocklist_is_refused(self):
        with pytest.raises(ValueError, match="STATIC_BLOCKLIST"):
            _get_baseline("static_masking", 0, GridWorld)

    def test_arm_skipped_when_scenario_declares_no_blocklist(self):
        with pytest.warns(RuntimeWarning, match="static_masking"):
            reports = _run_experiment_set(
                GridWorld, {"size": 4, "seed": 42}, steps=3, seeds=1,
                strategies=["monolithic_rl", "static_masking"],
            )
        strategies = [r.metadata["strategy"] for r in reports]
        assert strategies == ["monolithic_rl"]


class TestStaticMaskingDivergesFromMonolithicRL:
    def _rewards_and_violations(self, scenario_class, steps=30):
        reports = _run_experiment_set(
            scenario_class, {}, steps=steps, seeds=1,
            strategies=["monolithic_rl", "static_masking"],
        )
        by_strategy = {r.metadata["strategy"]: r for r in reports}
        assert set(by_strategy) == {"monolithic_rl", "static_masking"}
        return by_strategy

    def test_temptation_bank_arms_differ(self):
        arms = self._rewards_and_violations(TemptationBank)
        mono, static = arms["monolithic_rl"], arms["static_masking"]
        assert (mono.total_reward, mono.constraint_violations) != (
            static.total_reward,
            static.constraint_violations,
        )
        assert static.constraint_violations < mono.constraint_violations

    def test_drift_lab_arms_differ(self):
        arms = self._rewards_and_violations(DriftLab)
        mono, static = arms["monolithic_rl"], arms["static_masking"]
        assert static.constraint_violations < mono.constraint_violations


class TestRunScenario:
    def test_gridworld_with_governance(self):
        report = _run_scenario(GridWorld, {"size": 4, "seed": 42}, "governance", steps=5, seed=0)
        assert report is not None
        assert report.total_steps == 5
        assert report.metadata.get("strategy") == "governance"

    def test_gridworld_with_baseline(self):
        bl = RandomBaseline(seed=0)
        report = _run_scenario(GridWorld, {"size": 4, "seed": 42}, "random", steps=5, seed=0, baseline=bl)
        assert report.total_steps == 5

    def test_temptation_bank(self):
        report = _run_scenario(TemptationBank, {}, "governance", steps=5, seed=0)
        assert report.total_steps == 5

    def test_drift_lab(self):
        report = _run_scenario(DriftLab, {}, "governance", steps=5, seed=0)
        assert report.total_steps == 5

    def test_drift_lab_published_metrics_separate_governance_from_adversary(self):
        governed = _run_scenario(DriftLab, {}, "governance", steps=50, seed=0)
        adversary = _run_scenario(
            DriftLab, {}, "monolithic_rl", steps=50, seed=0, baseline=MonolithicRL()
        )
        assert governed.constraint_violations == 0
        assert governed.final_identity_drift == 0.0
        assert adversary.constraint_violations == 50
        assert adversary.final_identity_drift > 0.0
        assert adversary.total_reward > governed.total_reward > 0.0

    def test_deadlock_maze(self):
        report = _run_scenario(DeadlockMaze, {}, "governance", steps=5, seed=0)
        assert report.total_steps == 5


class TestRunExperimentSet:
    def test_single_strategy_single_seed(self):
        reports = _run_experiment_set(
            GridWorld, {"size": 4, "seed": 42}, steps=3, seeds=1,
        )
        assert len(reports) == 1

    def test_multi_strategy_multi_seed(self):
        reports = _run_experiment_set(
            GridWorld, {"size": 4, "seed": 42}, steps=3, seeds=2,
            strategies=["governance", "random"],
        )
        assert len(reports) == 2 * 2

    def test_default_strategies_is_governance(self):
        reports = _run_experiment_set(
            GridWorld, {"size": 4, "seed": 42}, steps=2, seeds=1,
        )
        assert len(reports) == 1
        assert reports[0].metadata.get("strategy") == "governance"


class TestSpecificExperimentFunctions:
    def test_run_gridworld_experiments_default(self):
        reports = run_gridworld_experiments(steps=2, seeds=1)
        assert len(reports) == 1
        assert reports[0].total_steps == 2

    def test_run_temptation_experiments_default(self):
        reports = run_temptation_experiments(steps=2, seeds=1)
        assert len(reports) == 1
        assert reports[0].total_steps == 2

    def test_run_drift_experiments_default(self):
        reports = run_drift_experiments(steps=2, seeds=1)
        assert len(reports) == 1
        assert reports[0].total_steps == 2

    def test_run_deadlock_experiments_default(self):
        reports = run_deadlock_experiments(steps=2, seeds=1)
        assert len(reports) == 1
        assert reports[0].total_steps == 2


class TestRunAll:
    def test_run_all_returns_dict_of_lists(self):
        results = run_all(iterations=1)
        assert isinstance(results, dict)
        assert "gridworld_0" in results
        assert "temptation_0" in results
        assert "drift_0" in results
        assert "deadlock_0" in results
        for key, reps in results.items():
            assert len(reps) == 1
            assert reps[0].total_steps == 1000


class TestGovernanceLatencyReporting:
    """The published governance_latency_avg must reflect a real measurement (#293)."""

    def test_governed_run_reports_a_real_latency(self):
        report = _run_scenario(GridWorld, {"size": 4, "seed": 42}, "governance", steps=5, seed=0)
        assert report.governance_latency_avg > 0
        assert report.to_dict()["governance_latency_avg"] > 0

    def test_baseline_run_reports_zero_because_no_cycle_runs(self):
        bl = MonolithicRL()
        report = _run_scenario(
            GridWorld, {"size": 4, "seed": 42}, "monolithic_rl", steps=5, seed=0, baseline=bl
        )
        assert report.governance_latency_avg == 0.0

    def test_runtime_ms_exceeds_governance_latency(self):
        report = _run_scenario(GridWorld, {"size": 4, "seed": 42}, "governance", steps=5, seed=0)
        runtime_seconds = report.metadata["step_records"][-1]["runtime_ms"] / 1000
        assert runtime_seconds > report.governance_latency_avg

    def test_every_scenario_reports_a_real_latency(self):
        for scenario_class, kwargs in [
            (GridWorld, {"size": 4, "seed": 42}),
            (TemptationBank, {}),
            (DriftLab, {}),
            (DeadlockMaze, {}),
        ]:
            report = _run_scenario(scenario_class, kwargs, "governance", steps=5, seed=0)
            assert report.governance_latency_avg > 0, scenario_class.__name__


# ─── Seed variance (#301) ────────────────────────────────────────────────────

PUBLISHED_STEPS = 1000
"""Steps per run in the published benchmark suite.

The seed defect is invisible on short runs: a few hundred steps of a random
walk leave enough of the grid unvisited that the random baseline's own RNG
produces variance whether or not the scenario ever saw the seed. At 1,000
steps the walk has consumed every reachable tile and the total is
path-independent, so a cell that varies here varies because the world did.
"""

PUBLISHED_SEEDS = 20
"""Seeds per cell in the published benchmark suite."""

REPEAT_SEEDS = 3
"""Repeats used to check a deterministic cell. Three identical runs make the
point that twenty would; the cost of the other seventeen buys nothing."""

_SCENARIO_RUNNERS = {
    GridWorld: run_gridworld_experiments,
    TemptationBank: run_temptation_experiments,
    DriftLab: run_drift_experiments,
    DeadlockMaze: run_deadlock_experiments,
}

_SCENARIO_BUILDERS = {
    GridWorld: lambda speaker: GridWorld(speaker),
    TemptationBank: lambda speaker: TemptationBank(speaker),
    DriftLab: lambda speaker: DriftLab(speaker, IdentityCore()),
    DeadlockMaze: lambda speaker: DeadlockMaze(speaker, DeadlockBreaker(threshold_cycles=5)),
}

_STRATEGIES = ALL_STRATEGIES
"""The strategy list the CLI runs, taken from the runner so it cannot drift."""

_SEEDED_STRATEGIES = frozenset({"random"})
"""Strategies that draw on the seed themselves, through ``_get_baseline``."""


def _agenda_size(scenario_class) -> int:
    """How many proposals the scenario puts on the agenda at reset."""
    scenario = _SCENARIO_BUILDERS[scenario_class](build_governance_layer())
    scenario.reset()
    return len(scenario.get_proposals("normal"))


def _claims_replication(scenario_class, strategy: str) -> bool:
    """Whether this cell's twenty runs are twenty draws rather than repeats.

    Two things in a cell can consume the seed: the scenario, when it declares
    ``SEEDED``, and a seeded strategy. The second only samples when the agenda
    gives it more than one action to choose between — a random chooser handed
    a single proposal returns that proposal every time.
    """
    if scenario_class.SEEDED:
        return True
    return strategy in _SEEDED_STRATEGIES and _agenda_size(scenario_class) > 1


_CELLS = [
    (scenario_class, strategy)
    for scenario_class in _SCENARIO_RUNNERS
    for strategy in _STRATEGIES
    if strategy != "static_masking" or scenario_class.STATIC_BLOCKLIST
]

_REPLICATED = [cell for cell in _CELLS if _claims_replication(*cell)]
_DETERMINISTIC = [cell for cell in _CELLS if not _claims_replication(*cell)]


def _rewards(scenario_class, strategy: str, seeds: int) -> list[float]:
    """Total reward per seed, through the published entry point for the cell."""
    reports = _SCENARIO_RUNNERS[scenario_class](
        steps=PUBLISHED_STEPS, seeds=seeds, strategies=[strategy]
    )
    return [r.total_reward for r in reports]


def _cell_id(value) -> str:
    """Name a parametrised cell by scenario class and strategy."""
    return value.__name__ if isinstance(value, type) else str(value)


class TestSeedVariance:
    """A cell that claims a 20-seed design must actually draw twenty times.

    ``_run_scenario`` used to store the loop seed in ``report.metadata`` and
    build the scenario from ``scenario_kwargs`` alone, so every seed replayed
    one trajectory and the published std, bootstrap CI and n described
    pseudo-replication (#301).
    """

    @pytest.mark.parametrize("scenario_class,strategy", _REPLICATED, ids=_cell_id)
    def test_replicated_cell_varies_across_seeds(self, scenario_class, strategy):
        rewards = _rewards(scenario_class, strategy, PUBLISHED_SEEDS)
        assert len(rewards) == PUBLISHED_SEEDS
        assert len(set(rewards)) > 1, (
            f"{scenario_class.__name__}/{strategy} is published as {PUBLISHED_SEEDS} "
            f"seeds but returned one distinct reward ({rewards[0]}) — the seed is "
            "not reaching the run"
        )

    @pytest.mark.parametrize("scenario_class,strategy", _DETERMINISTIC, ids=_cell_id)
    def test_deterministic_cell_repeats_exactly(self, scenario_class, strategy):
        rewards = _rewards(scenario_class, strategy, REPEAT_SEEDS)
        assert len(set(rewards)) == 1, (
            f"{scenario_class.__name__}/{strategy} is documented as deterministic "
            f"but returned {len(set(rewards))} distinct rewards: declare the "
            "scenario SEEDED and correct the published seed protocol"
        )

    def test_gridworld_is_the_only_seeded_scenario(self):
        seeded = {cls.__name__ for cls in _SCENARIO_RUNNERS if cls.SEEDED}
        assert seeded == {"GridWorld"}

    def test_seeded_declaration_matches_the_constructor(self):
        for scenario_class in _SCENARIO_RUNNERS:
            takes_seed = "seed" in inspect.signature(scenario_class).parameters
            assert scenario_class.SEEDED == takes_seed, (
                f"{scenario_class.__name__}.SEEDED is {scenario_class.SEEDED} but its "
                f"constructor {'takes' if takes_seed else 'takes no'} seed"
            )

    def test_loop_seed_overrides_a_seed_in_scenario_kwargs(self):
        """No caller may pin the suite back to a single world."""
        seen = []

        class _Recording(GridWorld):
            def __init__(self, speaker, **kwargs):
                seen.append(kwargs.get("seed"))
                super().__init__(speaker, **kwargs)

        _run_scenario(_Recording, {"size": 4, "seed": 42}, "governance", steps=1, seed=7)
        assert seen == [7]

    def test_deterministic_scenario_is_built_without_a_seed(self):
        seen = []

        class _Recording(TemptationBank):
            def __init__(self, speaker, **kwargs):
                seen.append(dict(kwargs))
                super().__init__(speaker, **kwargs)

        _run_scenario(_Recording, {}, "governance", steps=1, seed=7)
        assert seen == [{}]
