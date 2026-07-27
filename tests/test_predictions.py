import pytest
from src.governance.prove.predictions import (
    ALL_PREDICTIONS,
    PredictionResult,
    pred_01_budget_enforcement,
    pred_02_priority_ordering,
    pred_03_weighted_vote,
    pred_04_tag_compliance_budget,
    pred_05_contract_restricts,
    pred_06_revocation_harder,
    pred_07_timelock,
    pred_08_mask_composition,
    pred_09_coherence_veto,
    pred_10_tier4_multisig,
    pred_11_genesis_multisig,
    pred_12_deadlock_breaker,
    _build_speaker,
)


class TestBuildSpeaker:
    def test_returns_speaker_with_5_members(self):
        speaker = _build_speaker()
        assert len(speaker.members) == 5
        assert "reward" in speaker.members
        assert "safety" in speaker.members
        assert "integrity" in speaker.members
        assert "planning" in speaker.members
        assert "curiosity" in speaker.members
        assert speaker.default_action == "emergency_shutdown"


class TestPredictionResult:
    def test_dataclass_fields(self):
        r = PredictionResult(id=1, chapter="Ch2", section="3.1", description="test", passed=True, evidence="ok")
        assert r.id == 1
        assert r.chapter == "Ch2"
        assert r.passed is True


class TestAllPredictions:
    def test_all_predictions_pass(self):
        results = []
        for fn in ALL_PREDICTIONS:
            try:
                result = fn()
            except Exception as e:
                result = PredictionResult(
                    id=ALL_PREDICTIONS.index(fn) + 1,
                    chapter="ERR", section="0",
                    description=fn.__name__,
                    passed=False,
                    evidence=f"Exception: {e}",
                )
            results.append(result)
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0, (
            f"{len(failed)} predictions failed:\n" +
            "\n".join(f"  P{r.id:02d} ({r.chapter} ??{r.section}): {r.evidence}" for r in failed)
        )

    def test_all_predictions_list_length(self):
        assert len(ALL_PREDICTIONS) == 12

    def test_all_predictions_have_unique_ids(self):
        results = []
        for i, fn in enumerate(ALL_PREDICTIONS):
            result = fn()
            assert result.id == i + 1
            results.append(result)
        ids = [r.id for r in results]
        assert len(set(ids)) == 12


class TestPred01BudgetEnforcement:
    def test_budget_enforces_proposal_cap(self):
        result = pred_01_budget_enforcement()
        assert result.passed, result.evidence
        assert result.id == 1
        assert result.chapter == "Ch2"

    def test_agenda_shorter_or_equal_to_budget(self):
        speaker = _build_speaker()
        budget = speaker.members["reward"].budget
        from src.governance.models import PriorityTag, Proposal
        import time
        proposals = [
            Proposal(member_id="reward", action=f"a_{i}", tag=PriorityTag.ROUTINE,
                     timestamp=time.time(), metadata={})
            for i in range(budget + 5)
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) <= budget


class TestPred02PriorityOrdering:
    def test_critical_safety_first(self):
        result = pred_02_priority_ordering()
        assert result.passed, result.evidence


class TestPred03WeightedVote:
    def test_weighted_vote_matches_spec(self):
        result = pred_03_weighted_vote()
        assert result.passed, result.evidence


class TestPred04TagCompliance:
    def test_budget_halved_after_falsifications(self):
        result = pred_04_tag_compliance_budget()
        assert result.passed, result.evidence

    def test_budget_unchanged_with_good_proposals(self):
        speaker = _build_speaker()
        initial = speaker.members["reward"].budget
        from src.governance.models import PriorityTag, Proposal
        import time
        proposals = [
            Proposal(member_id="reward", action=f"good_{i}", tag=PriorityTag.ROUTINE,
                     timestamp=time.time(),
                     metadata={"expected_reward": 1.0, "risk": 0.0, "identity_coherence": 1.0})
            for i in range(min(3, initial))
        ]
        speaker.run_governance_cycle("normal", proposals, "routine")
        assert speaker.members["reward"].budget == initial


class TestPred05ContractRestricts:
    def test_contract_restricts_action_set(self):
        result = pred_05_contract_restricts()
        assert result.passed, result.evidence

    def test_contract_only_restricts_specified_indices(self):
        from src.governance.contracts.contract import UlyssesContract
        c = UlyssesContract("test", {7}, 0.66, 1.0)
        c.enact()
        assert c.applies_to(7) is True
        assert c.applies_to(1) is False
        assert c.applies_to(8) is False


class TestPred06RevocationHarder:
    def test_revocation_harder_than_enactment(self):
        result = pred_06_revocation_harder()
        assert result.passed, result.evidence

    def test_default_thresholds(self):
        from src.governance.contracts.contract import UlyssesContract
        c = UlyssesContract("t", {7}, 0.66, 1.0)
        assert c.revocation_threshold > c.enactment_threshold


class TestPred07Timelock:
    def test_timelock_blocks_early_revocation(self):
        result = pred_07_timelock()
        assert result.passed, result.evidence


class TestPred08MaskComposition:
    def test_mask_composition(self):
        result = pred_08_mask_composition()
        assert result.passed, result.evidence

    def test_empty_restrictions(self):
        from src.governance.contracts.merger import apply_restrictions
        assert apply_restrictions({1, 2, 3}, set()) == {1, 2, 3}

    def test_all_restricted(self):
        from src.governance.contracts.merger import apply_restrictions
        assert apply_restrictions({1, 2}, {1, 2}) == set()


class TestPred09CoherenceVeto:
    def test_low_coherence_triggers_veto(self):
        result = pred_09_coherence_veto()
        assert result.passed, result.evidence


class TestPred10Tier4Multisig:
    def test_tier4_requires_multisig(self):
        result = pred_10_tier4_multisig()
        assert result.passed, result.evidence

    def test_tier_rules_structure(self):
        from src.governance.identity.tiers import MutabilityTier, TIER_RULES
        assert TIER_RULES[MutabilityTier.CONSTITUTIONAL].requires_external_multisig is True
        assert TIER_RULES[MutabilityTier.OPERATIONAL].requires_external_multisig is False
        assert TIER_RULES[MutabilityTier.DYNAMIC].requires_external_multisig is False


class TestPred11GenesisMultisig:
    def test_genesis_3_of_5_multisig(self):
        result = pred_11_genesis_multisig()
        assert result.passed, result.evidence


class TestPred12DeadlockBreaker:
    def test_deadlock_breaker_fires(self):
        result = pred_12_deadlock_breaker()
        assert result.passed, result.evidence

    def test_breaker_does_not_fire_before_threshold(self):
        from src.governance.tee.watchdog import DeadlockBreaker
        breaker = DeadlockBreaker(threshold_cycles=5)
        for _ in range(4):
            breaker.record_cycle(decision_produced=False)
            assert not breaker.check()
