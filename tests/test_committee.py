import pytest

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


class TestMemberRegistration:
    def test_reward_member_attributes(self):
        m = ExampleRewardMember()
        assert m.member_id == "reward"
        assert m.veto_threshold == 0.0
        assert m.weight == 1.0
        assert m.budget == 3

    def test_safety_member_weight_higher(self):
        m = ExampleSafetyMember()
        assert m.weight == 2.0
        assert m.veto_threshold == 0.5
        assert m.budget == 5

    def test_integrity_member_highest_weight(self):
        m = ExampleIntegrityMember()
        assert m.weight == 3.0
        assert m.veto_threshold == 0.8
        assert m.budget == 5

    def test_all_seven_members_unique_ids(self):
        members = [
            ExampleRewardMember(), ExampleSafetyMember(),
            ExampleCuriosityMember(), ExamplePlanningMember(),
            ExampleMemoryMember(), ExampleSocialMember(),
            ExampleIntegrityMember(),
        ]
        ids = [m.member_id for m in members]
        assert len(ids) == len(set(ids))

    def test_member_repr(self):
        m = ExampleRewardMember()
        r = repr(m)
        assert "ExampleRewardMember" in r
        assert "reward" in r


class TestProposalEvaluation:
    def test_reward_scores_expected_reward(self):
        m = ExampleRewardMember()
        p = Proposal(
            member_id="reward", action="test",
            metadata={"expected_reward": 0.9},
        )
        assert m.evaluate_proposal(None, p) == 0.9

    def test_safety_scores_inverse_risk(self):
        m = ExampleSafetyMember()
        p = Proposal(member_id="safety", action="test",
                     metadata={"risk": 0.2})
        assert m.evaluate_proposal(None, p) == 0.8

    def test_integrity_scores_coherence(self):
        m = ExampleIntegrityMember()
        p = Proposal(member_id="integrity", action="test",
                     metadata={"identity_coherence": 0.7})
        assert m.evaluate_proposal(None, p) == 0.7

    def test_curiosity_scores_novelty(self):
        m = ExampleCuriosityMember()
        p = Proposal(member_id="curiosity", action="test",
                     metadata={"novelty": 0.6})
        assert m.evaluate_proposal(None, p) == 0.6

    def test_planning_scores_long_term_value(self):
        m = ExamplePlanningMember()
        p = Proposal(member_id="planning", action="test",
                     metadata={"long_term_value": 0.7})
        assert m.evaluate_proposal(None, p) == 0.7

    def test_memory_scores_consistency(self):
        m = ExampleMemoryMember()
        p = Proposal(member_id="memory", action="test",
                     metadata={"historical_consistency": 0.8})
        assert m.evaluate_proposal(None, p) == 0.8

    def test_social_scores_acceptability(self):
        m = ExampleSocialMember()
        p = Proposal(member_id="social", action="test",
                     metadata={"social_acceptability": 0.75})
        assert m.evaluate_proposal(None, p) == 0.75

    def test_missing_metadata_defaults_to_zero(self):
        m = ExampleRewardMember()
        p = Proposal(member_id="reward", action="test")
        assert m.evaluate_proposal(None, p) == 0.0

    def test_safety_high_risk_low_score(self):
        m = ExampleSafetyMember()
        p = Proposal(member_id="safety", action="test",
                     metadata={"risk": 0.9})
        assert m.evaluate_proposal(None, p) == pytest.approx(0.1)

    def test_integrity_low_coherence_low_score(self):
        m = ExampleIntegrityMember()
        p = Proposal(member_id="integrity", action="test",
                     metadata={"identity_coherence": 0.0})
        assert m.evaluate_proposal(None, p) == 0.0


class TestProposalGeneration:
    def test_reward_proposes_exploit(self):
        m = ExampleRewardMember()
        p = m.propose("normal")
        assert p.action == "exploit"
        assert p.tag == PriorityTag.ROUTINE

    def test_safety_proposes_safe_action(self):
        m = ExampleSafetyMember()
        p = m.propose("normal")
        assert p.action == "safe_exploit"
        assert p.tag == PriorityTag.CRITICAL_SAFETY

    def test_curiosity_proposes_explore(self):
        m = ExampleCuriosityMember()
        p = m.propose("normal")
        assert p.action == "explore"
        assert p.tag == PriorityTag.EXPLORATORY

    def test_planning_proposes_strategic(self):
        m = ExamplePlanningMember()
        p = m.propose("normal")
        assert p.action == "strategic_action"
        assert p.tag == PriorityTag.HIGH_IMPACT

    def test_memory_proposes_maintain(self):
        m = ExampleMemoryMember()
        p = m.propose("normal")
        assert p.action == "maintain_course"
        assert p.tag == PriorityTag.INFORMATIONAL

    def test_social_proposes_cooperative(self):
        m = ExampleSocialMember()
        p = m.propose("normal")
        assert p.action == "cooperative_action"

    def test_integrity_proposes_principled(self):
        m = ExampleIntegrityMember()
        p = m.propose("normal")
        assert p.action == "maintain_course"
        assert p.tag == PriorityTag.HIGH_IMPACT


class TestConsensusRules:
    def test_all_scores_near_one(self):
        m1 = ExampleRewardMember()
        m2 = ExampleSafetyMember()
        p = Proposal(
            member_id="reward", action="test",
            metadata={"expected_reward": 1.0, "risk": 0.0, "identity_coherence": 1.0},
        )
        s1 = m1.evaluate_proposal(None, p)
        s2 = m2.evaluate_proposal(None, p)
        assert s1 == 1.0
        assert s2 == 1.0

    def test_conflicting_scores(self):
        m1 = ExampleRewardMember()
        m2 = ExampleSafetyMember()
        p = Proposal(
            member_id="reward", action="test",
            metadata={"expected_reward": 1.0, "risk": 0.9, "identity_coherence": 0.5},
        )
        assert m1.evaluate_proposal(None, p) == 1.0
        assert m2.evaluate_proposal(None, p) == pytest.approx(0.1)
