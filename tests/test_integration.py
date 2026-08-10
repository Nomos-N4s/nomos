"""End-to-end integration test: GridWorld with full Parliament."""

import pytest

from src.nomos.committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExampleMemoryMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
    ExampleSocialMember,
)
from src.nomos.contracts.contract import ContractRegistry, UlyssesContract
from src.nomos.contracts.merger import merge_masks
from src.nomos.models import GovernanceDecision, PriorityTag, Proposal
from src.nomos.speaker import SpeakerStateMachine


@pytest.fixture
def full_parliament():
    return SpeakerStateMachine(
        members={
            "reward": ExampleRewardMember(),
            "safety": ExampleSafetyMember(),
            "curiosity": ExampleCuriosityMember(),
            "planning": ExamplePlanningMember(),
            "memory": ExampleMemoryMember(),
            "social": ExampleSocialMember(),
            "integrity": ExampleIntegrityMember(),
        },
        default_action="emergency_shutdown",
        majority_threshold=0.5,
        supermajority_threshold=0.66,
        max_rounds=3,
    )


class TestFullGovernanceCycle:
    def test_proposal_passes_full_parliament(self, full_parliament):
        proposals = [
            Proposal(
                member_id="reward",
                action="safe_exploit",
                tag=PriorityTag.ROUTINE,
                metadata={
                    "expected_reward": 0.8, "risk": 0.1,
                    "identity_coherence": 0.9, "novelty": 0.3,
                    "long_term_value": 0.7, "historical_consistency": 0.9,
                    "social_acceptability": 0.8,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
        )
        assert not decision.is_default
        assert decision.action is not None
        assert "round" in decision.governance_meta
        assert "falsification_counts" in decision.governance_meta

    def test_poison_proposal_blocked_by_safety(self, full_parliament):
        proposals = [
            Proposal(
                member_id="reward",
                action="eat_poison",
                tag=PriorityTag.ROUTINE,
                metadata={
                    "expected_reward": 0.9, "risk": 0.9,
                    "identity_coherence": 0.1, "novelty": 0.5,
                    "long_term_value": 0.0, "historical_consistency": 0.0,
                    "social_acceptability": 0.0,
                },
            ),
            Proposal(
                member_id="safety",
                action="avoid_poison",
                tag=PriorityTag.CRITICAL_SAFETY,
                metadata={
                    "expected_reward": 0.3, "risk": 0.0,
                    "identity_coherence": 1.0, "novelty": 0.5,
                    "long_term_value": 0.9, "historical_consistency": 1.0,
                    "social_acceptability": 0.9,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
        )
        assert decision.action == "avoid_poison"
        assert not decision.is_default

    def test_all_proposals_vetoed_falls_back(self, full_parliament):
        proposals = [
            Proposal(
                member_id="reward",
                action="risky_gamble",
                tag=PriorityTag.ROUTINE,
                metadata={
                    "expected_reward": 0.8, "risk": 1.0,
                    "identity_coherence": 0.0, "novelty": 0.9,
                    "long_term_value": 0.0, "historical_consistency": 0.0,
                    "social_acceptability": 0.0,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
        )
        assert decision.is_default
        assert decision.action == "emergency_shutdown"

    def test_high_impact_requires_supermajority(self, full_parliament):
        proposals = [
            Proposal(
                member_id="planning",
                action="strategic_shift",
                tag=PriorityTag.HIGH_IMPACT,
                metadata={
                    "expected_reward": 0.5, "risk": 0.3,
                    "identity_coherence": 1.0, "novelty": 0.5,
                    "long_term_value": 0.8, "historical_consistency": 0.6,
                    "social_acceptability": 0.5,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
            decision_class="high_impact",
        )
        assert not decision.is_default

    def test_decision_trace_contains_all_members(self, full_parliament):
        proposals = [
            Proposal(
                member_id="reward",
                action="standard_action",
                tag=PriorityTag.ROUTINE,
                metadata={
                    "expected_reward": 0.6, "risk": 0.2,
                    "identity_coherence": 0.8, "novelty": 0.3,
                    "long_term_value": 0.5, "historical_consistency": 0.7,
                    "social_acceptability": 0.6,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
        )
        member_ids = {"reward", "safety", "curiosity", "planning",
                      "memory", "social", "integrity"}
        assert member_ids.issubset(decision.scores.keys())

    def test_budget_across_multiple_cycles(self, full_parliament):
        for _ in range(5):
            proposals = [
                Proposal(
                    member_id="reward",
                    action=f"action_{_}",
                    tag=PriorityTag.ROUTINE,
                    metadata={
                        "expected_reward": 0.6, "risk": 0.2,
                        "identity_coherence": 0.8,
                    },
                ),
            ]
            decision = full_parliament.run_governance_cycle(
                state="normal", raw_proposals=proposals,
            )
            assert decision.action is not None


class TestEndToEndWithContracts:
    def test_contract_restricts_action(self, full_parliament):
        reg = ContractRegistry()
        contract = UlyssesContract(
            contract_id="ban_loans",
            restricted_indices={1, 2},
        )
        contract.enact()
        reg.add(contract)
        decision = GovernanceDecision(
            action="test",
            governance_meta={"action_mask": [0, 1, 2, 3]},
        )
        merged = merge_masks(decision, reg)
        assert merged.governance_meta["final_action_count"] == 2

    def test_no_contracts_unchanged(self, full_parliament):
        reg = ContractRegistry()
        decision = GovernanceDecision(
            action="test",
            governance_meta={"action_mask": [0, 1, 2]},
        )
        merged = merge_masks(decision, reg)
        assert merged.governance_meta["final_action_count"] == 3

    def test_full_stack_simulation(self, full_parliament):
        proposals = [
            Proposal(
                member_id="safety",
                action="safe_move",
                tag=PriorityTag.CRITICAL_SAFETY,
                metadata={
                    "expected_reward": 0.4, "risk": 0.0,
                    "identity_coherence": 1.0, "novelty": 0.5,
                    "long_term_value": 0.9, "historical_consistency": 1.0,
                    "social_acceptability": 0.9,
                },
            ),
            Proposal(
                member_id="reward",
                action="greedy_move",
                tag=PriorityTag.ROUTINE,
                metadata={
                    "expected_reward": 1.0, "risk": 0.8,
                    "identity_coherence": 0.0, "novelty": 0.0,
                    "long_term_value": 0.0, "historical_consistency": 0.0,
                    "social_acceptability": 0.0,
                },
            ),
        ]
        decision = full_parliament.run_governance_cycle(
            state="normal", raw_proposals=proposals,
        )
        assert not decision.is_default
        assert decision.action == "safe_move"
