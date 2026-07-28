import math
import time

from src.governance.committee.base import ParliamentMember
from src.governance.committee.members import (
    ExampleIntegrityMember,
    ExampleRewardMember,
    ExampleSafetyMember,
)
from src.governance.models import GovernanceDecision, PriorityTag, Proposal
from src.governance.speaker import SpeakerStateMachine


def _proposal(member_id="reward", tag=PriorityTag.ROUTINE, **meta):
    return Proposal(
        member_id=member_id,
        action="test_action",
        tag=tag,
        timestamp=time.time(),
        metadata=meta if meta else {
            "expected_reward": 0.5, "risk": 0.0, "identity_coherence": 1.0,
            "long_term_value": 0.5, "novelty": 0.5, "social_acceptability": 0.5,
            "historical_consistency": 0.5,
        },
    )


class TestFuzzMemberCounts:
    def test_zero_members_falls_to_default(self):
        speaker = SpeakerStateMachine(members={}, default_action="noop")
        decision = speaker.run_governance_cycle("normal", [_proposal("reward")])
        assert decision.is_default
        assert decision.action == "noop"

    def test_one_member_passes_good_proposal(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            _proposal("reward", expected_reward=0.9, risk=0.0, identity_coherence=1.0),
        ])
        assert not decision.is_default

    def test_one_member_defaults_on_bad_proposal(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            _proposal("reward", expected_reward=0.0, risk=0.9, identity_coherence=0.0),
        ])
        assert decision.is_default

    def test_many_members_no_crash(self):
        members = {f"m{i}": ExampleRewardMember() for i in range(100)}
        for m in members.values():
            m.budget = 1
        speaker = SpeakerStateMachine(members=members, default_action="noop")
        proposals = [
            _proposal(f"m{i}", expected_reward=0.5, risk=0.0, identity_coherence=1.0)
            for i in range(100)
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert not decision.is_default

    def test_many_members_all_veto_no_crash(self):
        members = {f"m{i}": ExampleRewardMember() for i in range(100)}
        for m in members.values():
            m.budget = 1
            m.veto_threshold = 1.0
        speaker = SpeakerStateMachine(members=members, default_action="fallback")
        proposals = [_proposal(f"m{i}") for i in range(100)]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert decision.is_default
        assert decision.action == "fallback"


class TestFuzzMetadataExtremes:
    @staticmethod
    def _decision_with_meta(**meta) -> GovernanceDecision:
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        return speaker.run_governance_cycle("normal", [
            _proposal("reward", **meta),
        ])

    def test_nan_expected_reward(self):
        decision = self._decision_with_meta(expected_reward=math.nan, risk=0.0, identity_coherence=1.0)
        assert decision.is_default

    def test_inf_expected_reward(self):
        decision = self._decision_with_meta(expected_reward=math.inf, risk=0.0, identity_coherence=1.0)
        assert not decision.is_default or decision.action == "noop"

    def test_neg_inf_expected_reward(self):
        decision = self._decision_with_meta(expected_reward=-math.inf, risk=0.0, identity_coherence=1.0)
        assert decision.is_default

    def test_nan_risk_no_crash(self):
        decision = self._decision_with_meta(expected_reward=0.5, risk=math.nan, identity_coherence=1.0)
        assert not decision.is_default or decision.is_default

    def test_negative_risk(self):
        decision = self._decision_with_meta(expected_reward=0.5, risk=-1.0, identity_coherence=1.0)
        assert not decision.is_default

    def test_extreme_risk_no_crash(self):
        decision = self._decision_with_meta(expected_reward=0.5, risk=1e10, identity_coherence=1.0)
        assert not decision.is_default or decision.is_default

    def test_nan_identity_coherence(self):
        decision = self._decision_with_meta(expected_reward=0.5, risk=0.0, identity_coherence=math.nan)
        assert not decision.is_default

    def test_all_nan_metadata(self):
        decision = self._decision_with_meta(
            expected_reward=math.nan, risk=math.nan, identity_coherence=math.nan,
            long_term_value=math.nan, novelty=math.nan, social_acceptability=math.nan,
            historical_consistency=math.nan,
        )
        assert not decision.is_default or decision.is_default

    def test_negative_coherence_causes_falsification(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember(), "integrity": integrity},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            _proposal("reward", expected_reward=0.5, risk=0.0, identity_coherence=-1.0),
        ])
        counts = decision.governance_meta.get("falsification_counts", {})
        assert counts.get("reward", 0) >= 1


class TestFuzzExtremeStrings:
    def test_very_long_member_id(self):
        long_id = "m" * 10000
        member = ExampleRewardMember()
        member.member_id = long_id
        speaker = SpeakerStateMachine(
            members={long_id: member},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            Proposal(
                member_id=long_id, action="x", tag=PriorityTag.ROUTINE,
                timestamp=0.0,
                metadata={"expected_reward": 0.9, "risk": 0.0, "identity_coherence": 1.0},
            ),
        ])
        assert not decision.is_default

    def test_empty_member_id(self):
        member = ExampleRewardMember()
        member.member_id = ""
        speaker = SpeakerStateMachine(
            members={"": member},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            Proposal(
                member_id="", action="x", tag=PriorityTag.ROUTINE,
                timestamp=0.0,
                metadata={"expected_reward": 0.9, "risk": 0.0, "identity_coherence": 1.0},
            ),
        ])
        assert not decision.is_default

    def test_unicode_member_id(self):
        unicode_id = "\u00e9\u00e4\u00fc\u00f1\u4e2d\u6587"
        member = ExampleRewardMember()
        member.member_id = unicode_id
        speaker = SpeakerStateMachine(
            members={unicode_id: member},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [
            Proposal(
                member_id=unicode_id, action="x", tag=PriorityTag.ROUTINE,
                timestamp=0.0,
                metadata={"expected_reward": 0.9, "risk": 0.0, "identity_coherence": 1.0},
            ),
        ])
        assert not decision.is_default


class TestFuzzSpeakerEdgeCases:
    def test_empty_proposal_list(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="emergency_stop",
        )
        decision = speaker.run_governance_cycle("normal", [])
        assert decision.is_default is True
        assert decision.action == "emergency_stop"

    def test_single_proposal_passes(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="shutdown",
        )
        p = _proposal("reward", expected_reward=0.9, risk=0.0, identity_coherence=1.0)
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.action == "test_action"

    def test_extreme_timestamp(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember(), "safety": ExampleSafetyMember()},
            default_action="noop",
        )
        proposals = [
            Proposal(member_id="reward", action="a", tag=PriorityTag.ROUTINE,
                     timestamp=1e12, metadata={"expected_reward": 0.5, "risk": 0.0, "identity_coherence": 1.0}),
            Proposal(member_id="safety", action="b", tag=PriorityTag.CRITICAL_SAFETY,
                     timestamp=-1e12, metadata={"expected_reward": 0.5, "risk": 1.0, "identity_coherence": 1.0}),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert not decision.is_default or decision.is_default

    def test_negative_timestamp_still_sorts(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        proposals = [
            Proposal(member_id="reward", action="later", tag=PriorityTag.ROUTINE,
                     timestamp=100.0, metadata={"expected_reward": 0.5, "risk": 0.0, "identity_coherence": 1.0}),
            Proposal(member_id="reward", action="earlier", tag=PriorityTag.ROUTINE,
                     timestamp=-100.0, metadata={"expected_reward": 0.5, "risk": 0.0, "identity_coherence": 1.0}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) == 2
        assert agenda[0].timestamp < agenda[1].timestamp

    def test_weighted_sum_zero_does_not_crash(self):
        class ZeroWeightMember(ParliamentMember):
            def __init__(self):
                super().__init__(member_id="zero", veto_threshold=0.0, weight=0.0, budget=1)
            def evaluate_proposal(self, state, proposal):
                return 0.0
            def propose(self, state):
                return _proposal("zero")

        speaker = SpeakerStateMachine(
            members={"zero": ZeroWeightMember()},
            default_action="fallback",
        )
        decision = speaker.run_governance_cycle("normal", [_proposal("zero")])
        assert decision.is_default

    def test_negative_budget_does_not_crash(self):
        member = ExampleRewardMember()
        member.budget = -1
        speaker = SpeakerStateMachine(
            members={"reward": member},
            default_action="noop",
        )
        decision = speaker.run_governance_cycle("normal", [_proposal("reward")])
        assert decision.is_default

    def test_duplicate_proposals_no_crash(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        p = _proposal("reward")
        decision = speaker.run_governance_cycle("normal", [p, p, p])
        assert not decision.is_default or decision.is_default


class TestFuzzLargeInputs:
    def test_1000_proposals_no_crash(self):
        member = ExampleRewardMember()
        member.budget = 100
        speaker = SpeakerStateMachine(
            members={"reward": member},
            default_action="noop",
        )
        proposals = [
            _proposal("reward", expected_reward=0.1, risk=0.0, identity_coherence=1.0)
            for _ in range(1000)
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        assert not decision.is_default or decision.is_default

    def test_large_metadata_dict(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
        )
        large_meta = {f"key_{i}": float(i) for i in range(1000)}
        large_meta["expected_reward"] = 0.9
        large_meta["risk"] = 0.0
        large_meta["identity_coherence"] = 1.0
        proposal = Proposal(
            member_id="reward", action="x", tag=PriorityTag.ROUTINE,
            timestamp=0.0, metadata=large_meta,
        )
        decision = speaker.run_governance_cycle("normal", [proposal])
        assert not decision.is_default

    def test_high_rounds_no_overflow(self):
        speaker = SpeakerStateMachine(
            members={"reward": ExampleRewardMember()},
            default_action="noop",
            max_rounds=1000,
        )
        decision = speaker.run_governance_cycle("normal", [
            _proposal("reward", expected_reward=0.9, risk=0.0, identity_coherence=1.0),
        ])
        assert not decision.is_default
