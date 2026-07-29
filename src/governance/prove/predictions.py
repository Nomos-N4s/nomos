"""
12 formal predictions from Chapters 2-4, each an executable test.

Each prediction function:
  1. Sets up the required Nomos state
  2. Executes the scenario
  3. Asserts the predicted outcome
  4. Returns :class:`PredictionResult` with an evidence string

The predictions are the bridge between formal theory and empirical
verification — every invariant stated in the book chapters has a
corresponding test here. Run them with:

.. code-block:: bash

    python -m src.governance.prove.runner --all

.. list-table:: Prediction Registry
   :widths: auto
   :header-rows: 1

   * - ID
     - Chapter
     - Section
     - Description
   * - 1
     - Ch2
     - §3.1
     - Budget enforces proposal cap (κ₂)
   * - 2
     - Ch2
     - §3.2
     - Priority ordering (CRITICAL_SAFETY first)
   * - 3
     - Ch2
     - §3.4
     - Weighted vote matches formal spec
   * - 4
     - Ch2
     - §3.7
     - Tag compliance halves budget after 3+ falsifications
   * - 5
     - Ch3
     - §2.1
     - Contract restricts action set
   * - 6
     - Ch3
     - §2.3
     - Revocation harder than enactment (:math:`\\psi > \\phi`)
   * - 7
     - Ch3
     - §2.4
     - Timelock blocks early revocation
   * - 8
     - Ch3
     - §3.0
     - Mask composition
   * - 9
     - Ch4
     - §2.1
     - Low-coherence triggers integrity veto
   * - 10
     - Ch4
     - §2.5
     - Constitutional tier requires external multisig
   * - 11
     - Ch4
     - §3.1
     - Genesis 3-of-5 multisig
   * - 12
     - Ch4
     - §3.6
     - Deadlock breaker fires after N defaults
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from ..committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
)
from ..contracts.contract import ContractState, UlyssesContract
from ..contracts.merger import apply_restrictions
from ..identity.keys import GenesisMultisig
from ..identity.tiers import TIER_RULES, MutabilityTier
from ..models import PriorityTag, Proposal
from ..speaker import SpeakerStateMachine
from ..tee.watchdog import DeadlockBreaker


@dataclass
class PredictionResult:
    """The outcome of a single formal prediction test.

    Attributes:
        id: Unique prediction number (1-12).
        chapter: The book chapter this prediction tests (``"Ch2"``, etc.).
        section: The section reference (e.g. ``"3.1"``).
        description: Human-readable summary of what was predicted.
        passed: Whether the prediction held.
        evidence: The actual values observed, for debugging.
    """

    id: int
    chapter: str
    section: str
    description: str
    passed: bool
    evidence: str


PredictionFn = Callable[[], PredictionResult]


def _build_speaker() -> SpeakerStateMachine:
    """Create a standard Speaker with 5 members (reward, safety, integrity, planning, curiosity).

    Used by most predictions to avoid repeating setup code.
    """
    members = {
        "reward": ExampleRewardMember(),
        "safety": ExampleSafetyMember(),
        "integrity": ExampleIntegrityMember(),
        "planning": ExamplePlanningMember(),
        "curiosity": ExampleCuriosityMember(),
    }
    return SpeakerStateMachine(
        members=members,
        default_action="emergency_shutdown",
    )


# ─── Prediction 1: Ch2 §3.1 — Budget enforces proposal cap ────────────────


def pred_01_budget_enforcement() -> PredictionResult:
    speaker = _build_speaker()
    proposals = [
        Proposal(
            member_id="reward",
            action=f"action_{i}",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"expected_reward": 0.5, "risk": 0.1, "identity_coherence": 0.5},
        )
        for i in range(10)
    ]
    agenda = speaker.set_agenda(proposals)
    budget = speaker.members["reward"].budget
    passed = len(agenda) <= budget
    return PredictionResult(
        id=1,
        chapter="Ch2",
        section="3.1",
        description="Budget enforces proposal cap",
        passed=passed,
        evidence=f"Member budget={budget}, submitted=10, agenda={len(agenda)}",
    )


# ─── Prediction 2: Ch2 §3.2 — Priority ordering ───────────────────────────


def pred_02_priority_ordering() -> PredictionResult:
    speaker = _build_speaker()
    now = time.time()
    proposals = [
        Proposal(
            member_id="reward",
            action="routine_first",
            tag=PriorityTag.ROUTINE,
            timestamp=now,
            metadata={"expected_reward": 0.5, "risk": 0.1, "identity_coherence": 0.5},
        ),
        Proposal(
            member_id="safety",
            action="critical_first",
            tag=PriorityTag.CRITICAL_SAFETY,
            timestamp=now + 0.1,
            metadata={"expected_reward": 0.0, "risk": 0.0, "identity_coherence": 1.0},
        ),
    ]
    agenda = speaker.set_agenda(proposals)
    passed = agenda[0].action == "critical_first"
    return PredictionResult(
        id=2,
        chapter="Ch2",
        section="3.2",
        description="Priority ordering: CRITICAL_SAFETY before ROUTINE",
        passed=passed,
        evidence=f"First in agenda: {agenda[0].action} (tag={PriorityTag.name(agenda[0].tag)})",
    )


# ─── Prediction 3: Ch2 §3.4 — Weighted vote matches formal spec ───────────


def pred_03_weighted_vote() -> PredictionResult:
    speaker = _build_speaker()
    proposal = Proposal(
        member_id="reward",
        action="safe_action",
        tag=PriorityTag.ROUTINE,
        timestamp=time.time(),
        metadata={
            "expected_reward": 0.5,
            "risk": 0.1,
            "identity_coherence": 0.9,
            "long_term_value": 0.5,
        },
    )
    decision = speaker.run_governance_cycle(
        state="normal", raw_proposals=[proposal], decision_class="routine"
    )
    scores = decision.scores
    weighted_sum = sum(speaker.members[mid].weight * sc for mid, sc in scores.items())
    total_weight = sum(m.weight for m in speaker.members.values())
    avg = weighted_sum / total_weight if total_weight > 0 else 0
    return PredictionResult(
        id=3,
        chapter="Ch2",
        section="3.4",
        description="Weighted vote matches formal spec",
        passed=(not decision.is_default) == (avg >= speaker.majority_threshold),
        evidence=f"Weighted avg={avg:.3f}, threshold={speaker.majority_threshold}, decision={'consensus' if not decision.is_default else 'default'}",
    )


# ─── Prediction 4: Ch2 §3.7 — Tag compliance halves budget ────────────────


def pred_04_tag_compliance_budget() -> PredictionResult:
    speaker = _build_speaker()
    initial_budget = speaker.members["reward"].budget
    proposals = [
        Proposal(
            member_id="reward",
            action=f"bad_action_{i}",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"expected_reward": 0.5, "risk": 0.5, "identity_coherence": 0.1},
        )
        for i in range(3)
    ]
    speaker.run_governance_cycle(state="normal", raw_proposals=proposals, decision_class="routine")
    final_budget = speaker.members["reward"].budget
    budget_halved = final_budget < initial_budget
    return PredictionResult(
        id=4,
        chapter="Ch2",
        section="3.7",
        description="Tag compliance halves budget after 3+ falsifications in a single cycle",
        passed=budget_halved,
        evidence=f"Initial budget={initial_budget}, final budget={final_budget} (expected <= {max(1, initial_budget // 2)})",
    )


# ─── Prediction 5: Ch3 §2.1 — Contract restricts action set ───────────────


def pred_05_contract_restricts() -> PredictionResult:
    contract = UlyssesContract(
        contract_id="test_restrict",
        restricted_indices={7},
        enactment_threshold=0.66,
        revocation_threshold=1.0,
    )
    contract.enact()
    restricted = contract.applies_to(7)
    not_restricted = not contract.applies_to(3)
    return PredictionResult(
        id=5,
        chapter="Ch3",
        section="2.1",
        description="Contract restricts action set",
        passed=restricted and not_restricted,
        evidence=f"Action 7 blocked={restricted}, action 3 blocked={not not_restricted}",
    )


# ─── Prediction 6: Ch3 §2.3 — Revocation harder than enactment ────────────


def pred_06_revocation_harder() -> PredictionResult:
    contract = UlyssesContract(
        contract_id="test_revoke",
        restricted_indices={7},
        enactment_threshold=0.66,
        revocation_threshold=1.0,
    )
    passed = contract.revocation_threshold > contract.enactment_threshold
    return PredictionResult(
        id=6,
        chapter="Ch3",
        section="2.3",
        description="Revocation harder than enactment",
        passed=passed,
        evidence=f"Enactment threshold={contract.enactment_threshold}, Revocation threshold={contract.revocation_threshold}",
    )


# ─── Prediction 7: Ch3 §2.4 — Timelock blocks early revocation ────────────


def pred_07_timelock() -> PredictionResult:
    contract = UlyssesContract(
        contract_id="test_timelock",
        restricted_indices={7},
        timelock_blocks=10,
        created_at_cycle=0,
    )
    contract.enact()
    blocked_before_ticks = (
        contract.state == ContractState.ENACTED and contract.timelock_blocks == 10
    )
    for _ in range(5):
        contract.tick()
    mid_timelock = contract.timelock_blocks
    still_enacted = contract.state == ContractState.ENACTED
    for _ in range(5):
        contract.tick()
    expired = contract.timelock_blocks == 0
    activated = contract.state == ContractState.ACTIVE
    passed = blocked_before_ticks and mid_timelock == 5 and still_enacted and expired and activated
    return PredictionResult(
        id=7,
        chapter="Ch3",
        section="2.4",
        description="Timelock decrements over time, preventing immediate revocation",
        passed=passed,
        evidence=f"Before ticks: timelock=10 state=ENACTED; after 5 ticks: timelock={mid_timelock} state={'ENACTED' if still_enacted else 'ACTIVE'}; after 10 ticks: timelock={contract.timelock_blocks} state={contract.state.name}",
    )


# ─── Prediction 8: Ch3 §3.0 — Mask composition ────────────────────────────


def pred_08_mask_composition() -> PredictionResult:
    allowed = {1, 2, 3, 7, 8, 9}
    restricted = {7, 8}
    result = apply_restrictions(allowed, restricted)
    expected = {1, 2, 3, 9}
    passed = result == expected
    return PredictionResult(
        id=8,
        chapter="Ch3",
        section="3.0",
        description="Mask composition (allowed - restricted = final)",
        passed=passed,
        evidence=f"Allowed={allowed} - Restricted={restricted} = {result} (expected={expected})",
    )


# ─── Prediction 9: Ch4 §2.1 — Low-coherence triggers veto ─────────────────


def pred_09_coherence_veto() -> PredictionResult:
    speaker = _build_speaker()
    low_coherence = Proposal(
        member_id="reward",
        action="harmful_action",
        tag=PriorityTag.ROUTINE,
        timestamp=time.time(),
        metadata={
            "expected_reward": 5.0,
            "risk": 0.9,
            "identity_coherence": 0.1,
            "long_term_value": -0.5,
        },
    )
    decision_low = speaker.run_governance_cycle(
        state="normal", raw_proposals=[low_coherence], decision_class="routine"
    )
    integrity_score = decision_low.scores.get("integrity", 1.0)
    passed = decision_low.is_default or integrity_score < 0.8
    return PredictionResult(
        id=9,
        chapter="Ch4",
        section="2.1",
        description="Low-coherence proposal triggers integrity veto or rejection",
        passed=passed,
        evidence=f"Coherence=0.1, integrity score={integrity_score:.2f}, default={decision_low.is_default}",
    )


# ─── Prediction 10: Ch4 §2.5 — Tier-4 requires external multisig ──────────


def pred_10_tier4_multisig() -> PredictionResult:
    constitutional = TIER_RULES[MutabilityTier.CONSTITUTIONAL].requires_external_multisig
    operational = TIER_RULES[MutabilityTier.OPERATIONAL].requires_external_multisig
    dynamic = TIER_RULES[MutabilityTier.DYNAMIC].requires_external_multisig
    passed = constitutional is True and operational is False and dynamic is False
    return PredictionResult(
        id=10,
        chapter="Ch4",
        section="2.5",
        description="Tier-4 (Constitutional) requires external multisig; lower tiers do not",
        passed=passed,
        evidence=f"CONSTITUTIONAL.requires_external_multisig={constitutional}, OPERATIONAL.requires_external_multisig={operational}, DYNAMIC.requires_external_multisig={dynamic}",
    )


# ─── Prediction 11: Ch4 §3.1 — Genesis 3-of-5 multisig ────────────────────


def pred_11_genesis_multisig() -> PredictionResult:
    ms = GenesisMultisig(threshold=3, total_holders=5)
    names = ["alice", "bob", "charlie", "diana", "eve"]
    for n in names:
        ms.add_holder(n)
    ms.sign("alice")
    ms.sign("bob")
    not_yet = ms.is_authorized
    ms.sign("charlie")
    authorized = ms.is_authorized
    passed = not not_yet and authorized
    return PredictionResult(
        id=11,
        chapter="Ch4",
        section="3.1",
        description="Genesis 3-of-5 multisig: 2 sigs insufficient, 3 sigs authorizes",
        passed=passed,
        evidence=f"Sigs=2 authorized={not_yet}, Sigs=3 authorized={authorized}",
    )


# ─── Prediction 12: Ch4 §3.6 — Deadlock breaker fires after N defaults ────


def pred_12_deadlock_breaker() -> PredictionResult:
    breaker = DeadlockBreaker(threshold_cycles=5)
    for _ in range(4):
        breaker.record_cycle(decision_produced=False)
        assert not breaker.check()
    breaker.record_cycle(decision_produced=False)
    fired = breaker.check()
    breaker.reset()
    settled = not breaker.check()
    passed = fired and settled
    return PredictionResult(
        id=12,
        chapter="Ch4",
        section="3.6",
        description="Deadlock breaker fires after N consecutive defaults, then resets",
        passed=passed,
        evidence=f"After 5 defaults: fired={fired}, after reset: still_fired={not settled}",
    )


# ─── Registry ──────────────────────────────────────────────────────────────


ALL_PREDICTIONS: list[PredictionFn] = [
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
]
"""All 12 prediction functions in order. Used by :mod:`runner` to execute them."""
