import time
import pytest
from src.governance.models import Proposal, PriorityTag, GovernanceDecision
from src.governance.committee.base import ParliamentMember
from src.governance.committee.members import (
    ExampleRewardMember, ExampleSafetyMember, ExampleIntegrityMember,
    ExampleCuriosityMember, ExamplePlanningMember, ExampleSocialMember,
    ExampleMemoryMember,
)
from src.governance.speaker import SpeakerStateMachine


def _make_proposal(member_id: str, tag: int = PriorityTag.ROUTINE,
                   risk: float = 0.0, reward: float = 0.5,
                   coherence: float = 1.0) -> Proposal:
    return Proposal(
        member_id=member_id,
        action=f"action_{member_id}",
        tag=tag,
        timestamp=time.time(),
        metadata={
            "expected_reward": reward,
            "risk": risk,
            "identity_coherence": coherence,
        },
    )


class TestSpeakerBudget:
    def test_budget_respected(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        proposals = [_make_proposal("reward") for _ in range(10)]
        filtered = speaker._apply_budgets(proposals)
        assert len(filtered) == reward.budget

    def test_budget_zero_points(self):
        member = ExampleRewardMember()
        member.budget = 0
        speaker = SpeakerStateMachine(
            members={"reward": member},
            default_action="shutdown",
        )
        proposals = [_make_proposal("reward")]
        filtered = speaker._apply_budgets(proposals)
        assert len(filtered) == 0

    def test_unknown_member_skipped(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        proposals = [_make_proposal("unknown")]
        filtered = speaker._apply_budgets(proposals)
        assert len(filtered) == 0

    def test_multiple_members_separate_budgets(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        proposals = [_make_proposal("reward") for _ in range(10)]
        proposals += [_make_proposal("safety") for _ in range(10)]
        filtered = speaker._apply_budgets(proposals)
        assert len(filtered) == reward.budget + safety.budget


class TestSpeakerPrioritySorting:
    def test_safety_first(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        proposals = [
            _make_proposal("reward", tag=PriorityTag.ROUTINE),
            _make_proposal("reward", tag=PriorityTag.CRITICAL_SAFETY),
            _make_proposal("reward", tag=PriorityTag.HIGH_IMPACT),
        ]
        sorted_p = speaker._sort_agenda(proposals)
        tags = [p.tag for p in sorted_p]
        assert tags == sorted(tags)

    def test_informational_last(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        proposals = [
            _make_proposal("reward", tag=PriorityTag.INFORMATIONAL),
            _make_proposal("reward", tag=PriorityTag.ROUTINE),
        ]
        sorted_p = speaker._sort_agenda(proposals)
        assert sorted_p[-1].tag == PriorityTag.INFORMATIONAL

    def test_set_agenda_integrates_budget_and_sort(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        raw = [_make_proposal("reward", tag=PriorityTag.ROUTINE) for _ in range(10)]
        raw[0].tag = PriorityTag.CRITICAL_SAFETY
        agenda = speaker.set_agenda(raw)
        assert len(agenda) <= ExampleRewardMember().budget
        assert agenda[0].tag == PriorityTag.CRITICAL_SAFETY


class TestSpeakerVeto:
    def test_member_vetoes_high_risk(self):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"safety": safety},
            default_action="shutdown",
        )
        p = _make_proposal("safety", risk=0.9)
        scores = speaker._score_proposal("normal", p)
        vetoers = speaker._check_vetoes(scores)
        assert "safety" in vetoers

    def test_low_risk_passes_veto(self):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"safety": safety},
            default_action="shutdown",
        )
        p = _make_proposal("safety", risk=0.1)
        scores = speaker._score_proposal("normal", p)
        vetoers = speaker._check_vetoes(scores)
        assert "safety" not in vetoers

    def test_vetoed_proposal_skipped_in_cycle(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        proposals = [
            _make_proposal("reward", risk=0.0, reward=1.0),
            _make_proposal("safety", risk=0.9, reward=0.0),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert decision.action == "action_reward"

    def test_all_vetoed_falls_to_default(self):
        reward = ExampleRewardMember()
        reward.veto_threshold = 1.0
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="emergency_shutdown",
        )
        p = _make_proposal("reward", risk=0.0, reward=0.0)
        scores = speaker._score_proposal("normal", p)
        vetoers = speaker._check_vetoes(scores)
        assert "reward" in vetoers


class TestSpeakerVoting:
    def test_majority_passes(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        p = _make_proposal("reward", risk=0.0, reward=1.0, coherence=1.0)
        scores = speaker._score_proposal("normal", p)
        passed = speaker._resolve_vote(scores, "routine")
        assert passed is True

    def test_supermajority_required_for_high_impact(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = _make_proposal("reward", risk=1.0, reward=0.0)
        scores = speaker._score_proposal("normal", p)
        passed = speaker._resolve_vote(scores, "high_impact")
        assert passed is False

    def test_identity_class_requires_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = _make_proposal("reward", reward=1.0, coherence=1.0)
        scores = speaker._score_proposal("normal", p)
        passed = speaker._resolve_vote(scores, "identity")
        assert passed is True

    def test_identity_class_fails_below_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = _make_proposal("reward", reward=0.8, coherence=1.0)
        scores = speaker._score_proposal("normal", p)
        passed = speaker._resolve_vote(scores, "identity")
        assert passed is False


class TestSpeakerQueueOverflow:
    def test_all_vetoed_triggers_default(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="emergency_shutdown",
        )
        proposals = [
            _make_proposal("reward", risk=0.9, reward=0.0),
            _make_proposal("safety", risk=0.9, reward=0.0),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert decision.is_default is True

    def test_max_rounds_exhausted(self):
        reward = ExampleRewardMember()
        reward.veto_threshold = 1.0
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="fallback",
            max_rounds=3,
        )
        proposals = [_make_proposal("reward", reward=0.5)]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert decision.is_default is True
        assert "No consensus" in decision.governance_meta["reason"]


class TestSpeakerFalsification:
    def test_falsification_counter_increments(self):
        integrity = ExampleIntegrityMember()
        reward = ExampleRewardMember()
        integrity.veto_threshold = 0.0
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            _make_proposal("reward", coherence=0.0),
            _make_proposal("integrity", coherence=1.0),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta["falsification_counts"]
        assert counts.get("reward", 0) >= 1

    def test_budget_halved_after_three_offenses_in_same_cycle(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        reward = ExampleRewardMember()
        initial_budget = reward.budget
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [_make_proposal("reward", coherence=0.0) for _ in range(5)]
        speaker.run_governance_cycle("normal", proposals)
        assert reward.budget <= initial_budget // 2

    def test_clean_proposals_no_falsification(self):
        integrity = ExampleIntegrityMember()
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            _make_proposal("reward", coherence=1.0),
            _make_proposal("integrity", coherence=1.0),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta["falsification_counts"]
        assert all(v == 0 for v in counts.values())


class TestSpeakerEdgeCases:
    def test_empty_proposals_returns_default(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [])
        assert decision.is_default is True
        assert decision.action == "noop"

    def test_single_proposal_passes(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = _make_proposal("reward", reward=1.0, coherence=1.0, risk=0.0)
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.action == "action_reward"

    def test_immutable_procedure_names(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        expected = [
            "agenda_budget_enforcement", "agenda_priority_sorting",
            "scoring_phase", "tag_compliance_check",
            "veto_phase", "voting_phase", "default_fallback",
        ]
        assert speaker.immutable_procedures == expected
