from src.governance.identity.core import (
    CommitmentThreshold,
    CommitmentType,
    CoreCommitment,
    EnforcementMode,
    IdentityCore,
)
from src.governance.identity.tiers import (
    TIER_RULES,
    MutabilityTier,
    TieredMutability,
)


class TestMutabilityTiers:
    def test_immutable_cannot_modify(self):
        rule = TIER_RULES[MutabilityTier.IMMUTABLE]
        assert not rule.can_modify(MutabilityTier.IMMUTABLE)

    def test_constitutional_can_modify(self):
        rule = TIER_RULES[MutabilityTier.CONSTITUTIONAL]
        assert rule.can_modify(MutabilityTier.CONSTITUTIONAL)

    def test_constitutional_requires_multisig(self):
        rule = TIER_RULES[MutabilityTier.CONSTITUTIONAL]
        assert rule.requires_external_multisig is True
        assert rule.requires_parliament_unanimity is True
        assert rule.cooling_off_days == 30

    def test_operational_threshold(self):
        rule = TIER_RULES[MutabilityTier.OPERATIONAL]
        assert "supermajority" in rule.modification_threshold
        assert rule.cooling_off_days == 7

    def test_dynamic_threshold(self):
        rule = TIER_RULES[MutabilityTier.DYNAMIC]
        assert "majority" in rule.modification_threshold
        assert rule.cooling_off_days == 0


class TestTieredMutability:
    def test_register_parameter(self):
        tm = TieredMutability()
        tm.register_parameter("max_risk", 0.5, MutabilityTier.OPERATIONAL)
        assert tm.get_tier("max_risk") == MutabilityTier.OPERATIONAL
        assert tm.get_value("max_risk") == 0.5

    def test_immutable_parameter_cannot_be_modified(self):
        tm = TieredMutability()
        tm.register_parameter("core_purpose", "safe_ai", MutabilityTier.IMMUTABLE)
        result = tm.propose_modification("core_purpose", "unsafe_ai")
        assert "Cannot modify immutable" in result

    def test_immutable_apply_returns_false(self):
        tm = TieredMutability()
        tm.register_parameter("core_purpose", "safe_ai", MutabilityTier.IMMUTABLE)
        assert not tm.apply_modification("core_purpose", "unsafe_ai")
        assert tm.get_value("core_purpose") == "safe_ai"

    def test_dynamic_parameter_can_modify(self):
        tm = TieredMutability()
        tm.register_parameter("exploration_rate", 0.1, MutabilityTier.DYNAMIC)
        result = tm.propose_modification("exploration_rate", 0.5)
        assert "Proposal accepted" in result

    def test_dynamic_apply_modification(self):
        tm = TieredMutability()
        tm.register_parameter("exploration_rate", 0.1, MutabilityTier.DYNAMIC)
        assert tm.apply_modification("exploration_rate", 0.5)
        assert tm.get_value("exploration_rate") == 0.5

    def test_unknown_parameter(self):
        tm = TieredMutability()
        result = tm.propose_modification("nonexistent", 1.0)
        assert "Unknown parameter" in result
        assert tm.get_tier("nonexistent") is None

    def test_operational_propose_message(self):
        tm = TieredMutability()
        tm.register_parameter("risk_limit", 0.3, MutabilityTier.OPERATIONAL)
        result = tm.propose_modification("risk_limit", 0.5)
        assert "supermajority" in result
        assert "7d" in result

    def test_get_all_params(self):
        tm = TieredMutability()
        tm.register_parameter("a", 1, MutabilityTier.IMMUTABLE)
        tm.register_parameter("b", 2, MutabilityTier.DYNAMIC)
        params = tm.get_all_params()
        assert params == {"a": 1, "b": 2}

    def test_tier_uniqueness(self):
        tiers = list(MutabilityTier)
        names = [t.name for t in tiers]
        assert len(names) == len(set(names))
        assert MutabilityTier.IMMUTABLE.value != MutabilityTier.DYNAMIC.value


class TestIdentityCore:
    def test_add_commitment(self):
        ic = IdentityCore()
        c = CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="Do no harm",
            threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
            enforcement=EnforcementMode.INTEGRITY_VETO,
        )
        ic.add_commitment(c)
        assert len(ic.commitments) == 1

    def test_identity_vector_generated(self):
        ic = IdentityCore()
        ic.add_commitment(CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="Do no harm",
            threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
            enforcement=EnforcementMode.INTEGRITY_VETO,
        ))
        ic.add_commitment(CoreCommitment(
            type=CommitmentType.BOUNDARY_CONDITION,
            statement="Never deceive",
            threshold=CommitmentThreshold.SUPERMAJORITY,
            enforcement=EnforcementMode.EXTERNAL_AUDIT,
        ))
        assert len(ic.identity_vector) == 2
        assert all(v == 1.0 for v in ic.identity_vector)

    def test_evaluate_coherence_no_commitments(self):
        ic = IdentityCore()
        assert ic.evaluate_coherence(0) == 1.0

    def test_evaluate_coherence_integrity_veto(self):
        ic = IdentityCore()
        ic.add_commitment(CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="No poison",
            threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
            enforcement=EnforcementMode.INTEGRITY_VETO,
            affected_action_indices=[1, 3],
        ))
        score_blocked = ic.evaluate_coherence(1)
        score_allowed = ic.evaluate_coherence(0)
        assert score_blocked < score_allowed

    def test_commitment_repr(self):
        c = CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="Do no harm",
            threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
            enforcement=EnforcementMode.INTEGRITY_VETO,
        )
        assert "value_principle" in repr(c)
