import pytest
from src.governance.models import PriorityTag, Proposal, GovernanceDecision
from src.governance.benchmarks.baselines import (
    MonolithicRL,
    RandomBaseline,
    StaticMasking,
    VetoOnly,
)


def make_proposal(member_id, action, expected_reward=0.0, risk=0.0):
    return Proposal(
        member_id=member_id,
        action=action,
        tag=PriorityTag.ROUTINE,
        metadata={"expected_reward": expected_reward, "risk": risk},
    )


class TestMonolithicRL:
    def test_picks_highest_reward(self):
        bl = MonolithicRL()
        proposals = [
            make_proposal("a", "bad", expected_reward=1.0),
            make_proposal("b", "good", expected_reward=10.0),
            make_proposal("c", "ok", expected_reward=5.0),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "good"
        assert d.governance_meta.get("policy") == "max_reward"

    def test_empty_proposals_default(self):
        bl = MonolithicRL()
        d = bl.decide(None, [])
        assert d.is_default
        assert d.action is None

    def test_tie_breaks_first_max(self):
        bl = MonolithicRL()
        proposals = [
            make_proposal("a", "first", expected_reward=5.0),
            make_proposal("b", "second", expected_reward=5.0),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "first"

    def test_name(self):
        assert MonolithicRL().name == "monolithic_rl"


class TestRandomBaseline:
    def test_picks_from_proposals(self):
        bl = RandomBaseline(seed=42)
        proposals = [
            make_proposal("a", "x"),
            make_proposal("b", "y"),
            make_proposal("c", "z"),
        ]
        for _ in range(20):
            d = bl.decide(None, proposals)
            assert d.action in ("x", "y", "z")
            assert d.governance_meta.get("policy") == "random"

    def test_deterministic_seed(self):
        bl1 = RandomBaseline(seed=99)
        bl2 = RandomBaseline(seed=99)
        proposals = [make_proposal("a", str(i)) for i in range(10)]
        d1 = bl1.decide(None, proposals)
        d2 = bl2.decide(None, proposals)
        assert d1.action == d2.action

    def test_empty_proposals_default(self):
        bl = RandomBaseline()
        d = bl.decide(None, [])
        assert d.is_default
        assert d.action is None

    def test_name(self):
        assert RandomBaseline(seed=0).name == "random"


class TestStaticMasking:
    def test_blocks_action(self):
        bl = StaticMasking(blocked_actions={"harmful"})
        proposals = [
            make_proposal("a", "harmful", expected_reward=100.0),
            make_proposal("b", "safe", expected_reward=1.0),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "safe"

    def test_no_blocked_all_allowed(self):
        bl = StaticMasking()
        proposals = [
            make_proposal("a", "x", expected_reward=1.0),
            make_proposal("b", "y", expected_reward=10.0),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "y"

    def test_all_blocked_default(self):
        bl = StaticMasking(blocked_actions={"a", "b"})
        proposals = [
            make_proposal("a", "a", expected_reward=5.0),
            make_proposal("b", "b", expected_reward=5.0),
        ]
        d = bl.decide(None, proposals)
        assert d.is_default
        assert d.action is None

    def test_empty_proposals_default(self):
        bl = StaticMasking()
        d = bl.decide(None, [])
        assert d.is_default

    def test_name(self):
        assert StaticMasking().name == "static_masking"


class TestVetoOnly:
    def test_accepts_safe_proposal(self):
        bl = VetoOnly(veto_threshold=0.3)
        proposals = [
            make_proposal("a", "risky", risk=0.9),
            make_proposal("b", "safe", risk=0.1),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "safe"
        assert d.governance_meta.get("policy") == "veto_only"

    def test_accepts_first_safe(self):
        bl = VetoOnly(veto_threshold=0.5)
        proposals = [
            make_proposal("a", "marginal", risk=0.4),
            make_proposal("b", "safest", risk=0.0),
        ]
        d = bl.decide(None, proposals)
        assert d.action == "marginal"

    def test_all_risky_default(self):
        bl = VetoOnly(veto_threshold=0.3)
        proposals = [
            make_proposal("a", "risky1", risk=0.8),
            make_proposal("b", "risky2", risk=0.9),
        ]
        d = bl.decide(None, proposals)
        assert d.is_default
        assert d.action is None

    def test_risk_equal_to_threshold_rejected(self):
        bl = VetoOnly(veto_threshold=0.5)
        proposals = [
            make_proposal("a", "borderline", risk=0.5),
        ]
        d = bl.decide(None, proposals)
        assert d.is_default

    def test_empty_proposals_default(self):
        bl = VetoOnly()
        d = bl.decide(None, [])
        assert d.is_default

    def test_name(self):
        assert VetoOnly().name == "veto_only"


class TestAllBaselines:
    def test_all_implement_decide_and_name(self):
        baselines = [
            MonolithicRL(),
            RandomBaseline(seed=0),
            StaticMasking(),
            VetoOnly(),
        ]
        proposals = [make_proposal("a", "action", expected_reward=1.0, risk=0.1)]
        for bl in baselines:
            d = bl.decide(None, proposals)
            assert hasattr(bl, "name")
            assert isinstance(bl.name, str)
            assert d.action == "action" or d.is_default
