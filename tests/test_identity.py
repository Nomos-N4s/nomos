import pytest

from src.nomos.identity.core import (
    COMPONENTS_PER_COMMITMENT,
    ENFORCEMENT_STRENGTH,
    THRESHOLD_STRENGTH,
    CommitmentThreshold,
    CommitmentType,
    CoreCommitment,
    EnforcementMode,
    IdentityCore,
)
from src.nomos.identity.tiers import (
    TIER_RULES,
    MutabilityTier,
    TieredMutability,
)


def _commitment(indices: list[int]) -> CoreCommitment:
    return CoreCommitment(
        type=CommitmentType.VALUE_PRINCIPLE,
        statement="Always classify honestly",
        threshold=CommitmentThreshold.SUPERMAJORITY,
        enforcement=EnforcementMode.INTEGRITY_VETO,
        affected_action_indices=indices,
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
        assert len(ic.identity_vector) == 2 * COMPONENTS_PER_COMMITMENT
        assert ic.identity_vector == [
            THRESHOLD_STRENGTH[CommitmentThreshold.UNANIMITY_MULTISIG],
            ENFORCEMENT_STRENGTH[EnforcementMode.INTEGRITY_VETO],
            1.0,
            THRESHOLD_STRENGTH[CommitmentThreshold.SUPERMAJORITY],
            ENFORCEMENT_STRENGTH[EnforcementMode.EXTERNAL_AUDIT],
            1.0,
        ]

    def test_identity_vector_distinguishes_commitment_strength(self):
        weak = IdentityCore()
        weak.add_commitment(CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="Do no harm",
            threshold=CommitmentThreshold.MAJORITY,
            enforcement=EnforcementMode.EXTERNAL_AUDIT,
        ))
        strong = IdentityCore()
        strong.add_commitment(CoreCommitment(
            type=CommitmentType.VALUE_PRINCIPLE,
            statement="Do no harm",
            threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
            enforcement=EnforcementMode.INTEGRITY_VETO,
        ))
        assert weak.identity_vector != strong.identity_vector

    def test_satisfaction_starts_at_one(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        assert ic.commitment_satisfaction == [1.0]

    def test_record_violation_degrades_matching_commitment(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        before = ic.identity_vector
        assert ic.record_violation(0, severity=0.5) == 1
        assert ic.commitment_satisfaction == [0.5]
        assert ic.identity_vector != before

    def test_record_violation_ignores_unaffected_commitment(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        before = ic.identity_vector
        assert ic.record_violation(1) == 0
        assert ic.commitment_satisfaction == [1.0]
        assert ic.identity_vector == before

    def test_record_violation_hits_every_action_when_indices_empty(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[]))
        assert ic.record_violation(7, severity=0.25) == 1
        assert ic.commitment_satisfaction == [0.75]

    def test_record_violation_decays_geometrically(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        for _ in range(3):
            ic.record_violation(0, severity=0.5)
        assert ic.commitment_satisfaction == [0.125]

    def test_record_violation_never_nulls_the_vector(self):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        for _ in range(500):
            ic.record_violation(0)
        assert 0.0 < ic.commitment_satisfaction[0] < 1e-6
        assert all(v > 0.0 for v in ic.identity_vector)

    @pytest.mark.parametrize("severity", [-0.1, 1.5])
    def test_record_violation_rejects_out_of_range_severity(self, severity):
        ic = IdentityCore()
        ic.add_commitment(_commitment(indices=[0]))
        with pytest.raises(ValueError):
            ic.record_violation(0, severity=severity)

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
