import pytest

from src.governance.experiments.base import ExperimentMetrics, ExperimentScenario, StepResult
from src.governance.experiments.drift_lab import DriftLab
from src.governance.models import GovernanceDecision, PriorityTag, Proposal
from src.governance.speaker import SpeakerStateMachine


def _gov(action="test", is_default=False, vetoed_by=None):
    return GovernanceDecision(action=action, governance_meta={"is_default": is_default},
                              vetoed_by=vetoed_by or [])


class TestStepResult:
    def test_dataclass_fields(self):
        decision = _gov(action="test")
        result = StepResult(decision=decision, state="running", reward=1.5)
        assert result.decision.action == "test"
        assert result.state == "running"
        assert result.reward == 1.5

    def test_default_reward(self):
        decision = _gov(action="idle", is_default=True)
        result = StepResult(decision=decision, state={})
        assert result.reward == 0.0


class TestExperimentMetrics:
    def test_defaults(self):
        m = ExperimentMetrics()
        assert m.total_steps == 0
        assert m.total_reward == 0.0
        assert m.constraint_violations == 0
        assert m.deadlock_count == 0
        assert m.contract_revocations == 0
        assert m.veto_count == 0
        assert m.falsification_count == 0
        assert m.identity_drift == []
        assert m.governance_latencies == []

    def test_increment_reward(self):
        m = ExperimentMetrics()
        m.total_reward += 5.0
        assert m.total_reward == 5.0

    def test_increment_deadlocks(self):
        m = ExperimentMetrics()
        m.deadlock_count += 1
        assert m.deadlock_count == 1

    def test_identity_drift_append(self):
        m = ExperimentMetrics()
        m.identity_drift.append(0.1)
        m.identity_drift.append(0.2)
        assert m.identity_drift == [0.1, 0.2]


class _ConcreteScenario(ExperimentScenario):
    def __init__(self):
        super().__init__(SpeakerStateMachine(members={}, default_action="stay"))

    def reset(self):
        self.metrics = ExperimentMetrics()

    def get_proposals(self, state):
        return [Proposal(member_id="reward", action="test", tag=PriorityTag.ROUTINE, timestamp=0.0, metadata={})]

    def compute_reward(self, state, decision):
        return 0.0

    def transition(self, state, decision):
        return state


class TestExperimentScenario:
    def test_history_immutable(self):
        decision = _gov(action="test")
        scenario = _ConcreteScenario()
        scenario._history.append(StepResult(decision=decision, state={}))
        hist = scenario.history
        assert len(hist) == 1
        hist.append(StepResult(decision=decision, state={}))
        assert len(scenario._history) == 1
        assert len(scenario.history) == 1

    def test_step_records_metrics(self):
        scenario = _ConcreteScenario()
        decision = _gov(action="test")
        result = scenario.step("state", external_decision=decision)
        assert isinstance(result, StepResult)
        assert scenario.metrics.total_steps == 1
        assert result.decision.action == "test"

    def test_step_counts_deadlock(self):
        scenario = _ConcreteScenario()
        default = _gov(action="default", is_default=True)
        scenario.step("state", external_decision=default)
        assert scenario.metrics.deadlock_count == 1
        assert scenario.metrics.total_steps == 1

    def test_step_counts_vetoes(self):
        scenario = _ConcreteScenario()
        vetoed = _gov(action="risky", vetoed_by=["safety"])
        scenario.step("state", external_decision=vetoed)
        assert scenario.metrics.veto_count == 1
        vetoed2 = _gov(action="risky2", vetoed_by=["safety", "integrity"])
        scenario.step("state", external_decision=vetoed2)
        assert scenario.metrics.veto_count == 3


# ─── GridWorld ───────────────────────────────────────────────────────────────


class TestGridWorld:
    def test_reset_creates_grid(self):
        from src.governance.experiments.grid_world import GridWorld
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        gw = GridWorld(speaker, size=4, seed=42, poison_ratio=0.5)
        gw.reset()
        assert len(gw._grid) == 4
        assert gw._pos == (0, 0)
        assert gw.metrics.total_steps == 0

    def test_get_proposals_returns_moves(self):
        from src.governance.experiments.grid_world import GridWorld
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        gw = GridWorld(speaker, size=4, seed=42)
        gw.reset()
        proposals = gw.get_proposals(None)
        assert len(proposals) <= 4
        for p in proposals:
            assert "expected_reward" in p.metadata
            assert "risk" in p.metadata
            assert "target" in p.metadata

    def test_poison_increments_violations(self):
        from src.governance.experiments.grid_world import TILE_EMPTY, TILE_POISON, GridWorld
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        gw = GridWorld(speaker, size=4, seed=0, poison_ratio=1.0)
        gw.reset()
        for row in gw._grid:
            for x in range(len(row)):
                if row[x] == TILE_POISON:
                    row[x] = TILE_EMPTY
        gw._grid[1][0] = TILE_POISON
        gw.step("state", external_decision=_gov(action="move_right"))
        assert gw.metrics.constraint_violations == 1
        assert gw.metrics.total_reward >= 5.0

    def test_timer_penalty_applied(self):
        from src.governance.experiments.grid_world import TILE_POISON, GridWorld
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        gw = GridWorld(speaker, size=4, seed=0, poison_ratio=1.0)
        gw.reset()
        gw._grid[1][0] = TILE_POISON
        gw.step("state", external_decision=_gov(action="move_right"))
        assert gw.metrics.total_reward == 5.0
        gw.step("state", external_decision=_gov(action="move_right"))
        gw.step("state", external_decision=_gov(action="move_right"))
        gw.step("state", external_decision=_gov(action="move_right"))
        assert gw.metrics.total_reward == 5.0 - 10.0

    def test_many_seeds_different_layouts(self):
        from src.governance.experiments.grid_world import GridWorld
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        layouts = set()
        for seed in range(10):
            gw = GridWorld(speaker, size=6, seed=seed)
            gw.reset()
            layouts.add(tuple(tuple(row) for row in gw._grid))
        assert len(layouts) == 10


# ─── TemptationBank ──────────────────────────────────────────────────────────


class TestTemptationBank:
    def test_reset(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker, initial_balance=100.0)
        tb.reset()
        assert tb.balance == 10.0
        assert tb._ban_proposed is False
        assert tb.metrics.total_steps == 0

    def test_get_proposals_includes_work(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        proposals = tb.get_proposals(None)
        assert any(p.action == "work" for p in proposals)

    def test_get_proposals_includes_loan_when_not_restricted(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        proposals = tb.get_proposals(None)
        assert any(p.action == "take_loan" for p in proposals)

    def test_get_proposals_excludes_loan_when_restricted(self):
        from src.governance.contracts.contract import UlyssesContract
        from src.governance.experiments.temptation_bank import TemptationBank
        tb = TemptationBank(SpeakerStateMachine(members={}, default_action="stay"))
        tb.reset()
        contract = UlyssesContract("ban_loans", restricted_indices={7}, enactment_threshold=0.66, revocation_threshold=1.0)
        contract.enact()
        tb.contracts.add(contract)
        proposals = tb.get_proposals(None)
        assert not any(p.action == "take_loan" for p in proposals)

    def test_get_proposals_includes_ban_once(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        p1 = tb.get_proposals(None)
        assert any(p.action == "propose_ban_loans" for p in p1)
        tb._ban_proposed = True
        p2 = tb.get_proposals(None)
        assert not any(p.action == "propose_ban_loans" for p in p2)

    def test_work_adds_reward(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        tb.step("state", external_decision=_gov(action="work"))
        assert tb.metrics.total_reward == 2.0
        assert tb.balance == 12.0

    def test_loan_adds_reward_and_violation(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        tb.step("state", external_decision=_gov(action="take_loan"))
        assert tb.metrics.total_reward == 10.0
        assert tb.metrics.constraint_violations == 1

    def test_ban_proposal_enacts_contract(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        tb.step("state", external_decision=_gov(action="propose_ban_loans"))
        assert tb._ban_proposed is True
        assert 7 in tb.contracts.active_restrictions()

    def test_loan_penalty_after_delay(self):
        from src.governance.experiments.temptation_bank import TemptationBank
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        tb = TemptationBank(speaker)
        tb.reset()
        tb.step("state", external_decision=_gov(action="take_loan"))
        assert tb.metrics.total_reward == 10.0
        for _ in range(11):
            tb.step("state", external_decision=_gov(action="work"))
        assert tb.metrics.total_reward == 10.0 + 11 * 2.0 - 15.0


# ─── DriftLab ────────────────────────────────────────────────────────────────


class TestDriftLab:
    def test_reset(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity, seed=42)
        dl.reset()
        assert dl._drift == 0.0
        assert dl.metrics.total_steps == 0

    def test_get_proposals_returns_two_actions(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity)
        dl.reset()
        proposals = dl.get_proposals(None)
        assert len(proposals) == 2
        actions = {p.action for p in proposals}
        assert actions == {"classify_harmful_as_safe", "classify_honestly"}

    def test_drift_increases_over_steps(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity, seed=42)
        dl.reset()
        assert dl._drift == 0.0
        dl.step("state", external_decision=_gov(action="classify_honestly"))
        assert dl._drift == 0.001
        dl.step("state", external_decision=_gov(action="classify_honestly"))
        assert dl._drift == 0.002

    def test_honest_action_no_violation(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity)
        dl.reset()
        dl.step("state", external_decision=_gov(action="classify_honestly"))
        assert dl.metrics.constraint_violations == 0

    def test_dishonest_action_counts_violation(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity)
        dl.reset()
        dl.step("state", external_decision=_gov(action="classify_harmful_as_safe"))
        assert dl.metrics.constraint_violations == 1

    def test_cosine_distance_identical(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert DriftLab._cosine_distance(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_cosine_distance_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert DriftLab._cosine_distance(a, b) == pytest.approx(2.0, abs=1e-6)

    def test_cosine_distance_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert DriftLab._cosine_distance(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_cosine_distance_empty_list(self):
        assert DriftLab._cosine_distance([], [1.0]) == 1.0
        assert DriftLab._cosine_distance([1.0], []) == 1.0

    def test_cosine_distance_zero_vector(self):
        assert DriftLab._cosine_distance([0.0, 0.0], [1.0, 0.0]) == 1.0

    def test_identity_drift_records_cosine_distance(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity)
        dl.reset()
        dl.step("state", external_decision=_gov(action="classify_honestly"))
        assert len(dl.metrics.identity_drift) == 1
        assert 0.0 <= dl.metrics.identity_drift[0] <= 2.0

    def test_honest_action_has_higher_coherence(self):
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.identity.core import IdentityCore
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        identity = IdentityCore()
        dl = DriftLab(speaker, identity)
        dl.reset()
        proposals = dl.get_proposals(None)
        honest = [p for p in proposals if p.action == "classify_honestly"][0]
        dishonest = [p for p in proposals if p.action == "classify_harmful_as_safe"][0]
        assert honest.metadata["identity_coherence"] > dishonest.metadata["identity_coherence"]


# ─── DeadlockMaze ────────────────────────────────────────────────────────────


class TestDeadlockMaze:
    def test_reset(self):
        from src.governance.experiments.deadlock_maze import PHASE_NORMAL, DeadlockMaze
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        dm = DeadlockMaze(speaker, breaker)
        dm.reset()
        assert dm._phase == PHASE_NORMAL
        assert dm.metrics.total_steps == 0

    def test_get_proposals_in_normal_phase(self):
        from src.governance.experiments.deadlock_maze import DeadlockMaze
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        dm = DeadlockMaze(speaker, breaker)
        dm.reset()
        proposals = dm.get_proposals(None)
        assert len(proposals) == 1
        assert proposals[0].action == "tighten_quorum"

    def test_quorum_tightening_triggers_deadlock_phase(self):
        from src.governance.experiments.deadlock_maze import PHASE_DEADLOCK, DeadlockMaze
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        dm = DeadlockMaze(speaker, breaker)
        dm.reset()
        dm.step("state", external_decision=_gov(action="tighten_quorum"))
        assert dm._phase == PHASE_DEADLOCK

    def test_default_decisions_count_as_deadlocks(self):
        from src.governance.experiments.deadlock_maze import DeadlockMaze
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        dm = DeadlockMaze(speaker, breaker)
        dm.reset()
        dm.step("state", external_decision=_gov(action="tighten_quorum"))
        for _ in range(3):
            dm.step("state", external_decision=_gov(action="default", is_default=True))
        assert dm.metrics.deadlock_count == 3

    def test_breaker_fires_and_recovers(self):
        from src.governance.experiments.deadlock_maze import (
            PHASE_DEADLOCK,
            PHASE_RECOVERED,
            DeadlockMaze,
        )
        from src.governance.identity.params import ParameterEnvelope
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        env = ParameterEnvelope()
        env.register("quorum_threshold", 0.5, (0.1, 1.0))
        dm = DeadlockMaze(speaker, breaker, params_envelope=env)
        dm.reset()
        dm.step("state", external_decision=_gov(action="tighten_quorum"))
        assert dm._phase == PHASE_DEADLOCK
        assert env.get("quorum_threshold") == 0.9
        for _ in range(5):
            dm.step("state", external_decision=_gov(action="default", is_default=True))
        assert dm._phase == PHASE_RECOVERED
        assert env.get("quorum_threshold") == 0.5

    def test_params_reset_to_defaults(self):
        from src.governance.experiments.deadlock_maze import DeadlockMaze
        from src.governance.identity.params import ParameterEnvelope
        from src.governance.tee.watchdog import DeadlockBreaker
        speaker = SpeakerStateMachine(members={}, default_action="stay")
        breaker = DeadlockBreaker(threshold_cycles=5)
        env = ParameterEnvelope()
        env.register("quorum_threshold", 0.5, (0.1, 1.0))
        dm = DeadlockMaze(speaker, breaker, params_envelope=env)
        dm.reset()
        dm.params.set("quorum_threshold", 0.9)
        assert dm.params.get("quorum_threshold") == 0.9
        dm.params.reset_to_defaults()
        assert dm.params.get("quorum_threshold") == 0.5


class TestExperimentConvention:
    """Verify all concrete scenarios follow the _run_step() convention."""

    def test_all_scenarios_override_run_step(self):
        from src.governance.experiments.deadlock_maze import DeadlockMaze
        from src.governance.experiments.drift_lab import DriftLab
        from src.governance.experiments.grid_world import GridWorld
        from src.governance.experiments.temptation_bank import TemptationBank

        scenarios = [GridWorld, TemptationBank, DriftLab, DeadlockMaze]
        for cls in scenarios:
            assert cls._run_step is not ExperimentScenario._run_step, (
                f"{cls.__name__} must override _run_step()"
            )
