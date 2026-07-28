from hypothesis import given
from hypothesis import strategies as st

from src.governance.committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExampleMemoryMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
    ExampleSocialMember,
)
from src.governance.models import PriorityTag, Proposal
from src.governance.speaker import SpeakerStateMachine

ALL_MEMBERS = {
    "reward": ExampleRewardMember(),
    "safety": ExampleSafetyMember(),
    "integrity": ExampleIntegrityMember(),
    "curiosity": ExampleCuriosityMember(),
    "planning": ExamplePlanningMember(),
    "social": ExampleSocialMember(),
    "memory": ExampleMemoryMember(),
}

MEMBER_IDS = list(ALL_MEMBERS.keys())

TAGS = st.sampled_from([
    PriorityTag.CRITICAL_SAFETY,
    PriorityTag.HIGH_IMPACT,
    PriorityTag.ROUTINE,
    PriorityTag.EXPLORATORY,
    PriorityTag.INFORMATIONAL,
])

META = st.fixed_dictionaries({
    "expected_reward": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "risk": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "identity_coherence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "long_term_value": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "novelty": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "social_acceptability": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "historical_consistency": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
})

PROPOSAL_STRATEGY = st.builds(
    Proposal,
    member_id=st.sampled_from(MEMBER_IDS),
    action=st.just("test_action"),
    tag=TAGS,
    timestamp=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
    metadata=META,
)


class TestPropertyBudgetInvariant:
    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=50))
    def test_budget_never_exceeded(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        total_budget = sum(m.budget for m in ALL_MEMBERS.values())
        assert len(agenda) <= total_budget

    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=50))
    def test_no_member_exceeds_individual_budget(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        counts = {}
        for p in agenda:
            counts[p.member_id] = counts.get(p.member_id, 0) + 1

        for member_id, member in ALL_MEMBERS.items():
            assert counts.get(member_id, 0) <= member.budget

    def test_unknown_members_skipped(self):
        speaker = SpeakerStateMachine(members={"reward": ExampleRewardMember()}, default_action="noop")
        proposals = [
            Proposal(member_id="unknown", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"risk": 0.0}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) == 0

    def test_budget_zero_excludes_all(self):
        member = ExampleRewardMember()
        member.budget = 0
        speaker = SpeakerStateMachine(members={"reward": member}, default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=float(i), metadata={"risk": 0.0})
            for i in range(5)
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) == 0


class TestPropertyPriorityOrder:
    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=30))
    def test_agenda_sorted_by_tag_then_timestamp(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        for i in range(1, len(agenda)):
            prev = agenda[i - 1]
            curr = agenda[i]
            key_prev = (prev.tag, prev.timestamp)
            key_curr = (curr.tag, curr.timestamp)
            assert key_prev <= key_curr, (
                f"Agenda not sorted at index {i}: "
                f"({prev.tag}, {prev.timestamp}) > ({curr.tag}, {curr.timestamp})"
            )

    def test_critical_safety_first(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="r", tag=PriorityTag.ROUTINE,
                     timestamp=1.0, metadata={}),
            Proposal(member_id="safety", action="s", tag=PriorityTag.CRITICAL_SAFETY,
                     timestamp=2.0, metadata={}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert agenda[0].tag == PriorityTag.CRITICAL_SAFETY

    def test_informational_last(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="r", tag=PriorityTag.INFORMATIONAL,
                     timestamp=1.0, metadata={}),
            Proposal(member_id="safety", action="s", tag=PriorityTag.ROUTINE,
                     timestamp=2.0, metadata={}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert agenda[-1].tag == PriorityTag.INFORMATIONAL


class TestPropertyDefaultFallback:
    def test_empty_proposals_returns_default(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="emergency_shutdown")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.is_default is True
        assert decision.action == "emergency_shutdown"

    def test_empty_proposals_all_members(self):
        speaker = SpeakerStateMachine(members={"reward": ExampleRewardMember()}, default_action="fallback")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.is_default is True

    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=20))
    def test_default_has_no_action_if_default_is_none(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action=None)
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=proposals)
        if decision.is_default:
            assert decision.action is None


class TestPropertyVetoBehavior:
    @given(risk=st.floats(min_value=0.9, max_value=1.0, allow_nan=False, allow_infinity=False))
    def test_high_risk_triggers_safety_veto(self, risk):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(members={"safety": safety}, default_action="shutdown")
        p = Proposal(member_id="safety", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.5, "risk": risk,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.is_default is True

    @given(risk=st.floats(min_value=0.0, max_value=0.3, allow_nan=False, allow_infinity=False))
    def test_low_risk_passes_safety_veto(self, risk):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(members={"safety": safety}, default_action="shutdown")
        p = Proposal(member_id="safety", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.5, "risk": risk,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        if not decision.is_default:
            assert decision.action == "x"


class TestPropertyFalsification:
    def test_clean_proposals_no_falsification(self):
        integrity = ExampleIntegrityMember()
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"identity_coherence": 1.0, "risk": 0.0,
                                               "expected_reward": 0.5}),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta.get("falsification_counts", {})
        assert all(v == 0 for v in counts.values())

    def test_low_coherence_triggers_falsification(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"identity_coherence": 0.0, "risk": 0.0,
                                               "expected_reward": 0.5}),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta.get("falsification_counts", {})
        assert counts.get("reward", 0) >= 1

    def test_budget_halved_after_three_offenses(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        reward = ExampleRewardMember()
        initial_budget = reward.budget
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=float(i), metadata={"identity_coherence": 0.0, "risk": 0.0,
                                                   "expected_reward": 0.5})
            for i in range(5)
        ]
        speaker.run_governance_cycle("normal", proposals)
        assert reward.budget <= initial_budget // 2


class TestPropertyVoting:
    def test_majority_passes_routine(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="good_action", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 1.0, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert not decision.is_default
        assert decision.action == "good_action"

    def test_high_impact_requires_supermajority(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="risky", tag=PriorityTag.HIGH_IMPACT,
                     timestamp=0.0, metadata={"expected_reward": 0.4, "risk": 1.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="high_impact")
        assert decision.is_default is True

    def test_identity_class_requires_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="identity_change", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.8, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="identity")
        assert decision.is_default is True

    def test_identity_class_passes_at_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="identity_change", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 1.0, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="identity")
        assert not decision.is_default

    @given(st.floats(min_value=0.0, max_value=0.3, allow_nan=False, allow_infinity=False))
    def test_low_expected_reward_fails_single_member(self, low_reward):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
            majority_threshold=0.5,
        )
        p = Proposal(member_id="reward", action="bad", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": low_reward, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.is_default is True


class TestPropertyAllMembersParticipate:
    def test_all_seven_members_present_on_consensus(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        meta = {
            "expected_reward": 0.8, "risk": 0.0, "identity_coherence": 1.0,
            "long_term_value": 0.9, "novelty": 0.7, "social_acceptability": 0.9,
            "historical_consistency": 1.0,
        }
        p = Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata=meta)
        decision = speaker.run_governance_cycle("normal", [p])
        assert len(decision.scores) == 7

    def test_default_decision_has_empty_scores(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.scores == {}
