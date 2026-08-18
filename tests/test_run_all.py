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
