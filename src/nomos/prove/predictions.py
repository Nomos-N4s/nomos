"""
12 formal predictions from Chapters 2-4, each an executable test.

Each prediction function:
  1. Sets up the required Nomos state
  2. Executes the scenario
  3. Asserts the predicted outcome
  4. Returns :class:`PredictionResult` with an evidence string

The predictions are the bridge between formal theory and empirical
verification — every invariant stated in the book chapters has a
corresponding test here. They are Python asserts over ``src/nomos/``: no
Lean runs when they do. :data:`LEAN_COVERAGE` records, per prediction, which
theorem of the Lean corpus in ``gov-budget-proof/`` states the same property
and which have no counterpart there at all. Run them with:

.. code-block:: bash

    python -m src.nomos.prove.runner --all

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
from enum import Enum

from ..committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
)
from ..contracts.contract import ContractState, UlyssesContract
from ..contracts.enforcement import enforce_timelock
from ..contracts.merger import apply_restrictions
from ..identity.keys import GenesisMultisig
from ..identity.tiers import TIER_RULES, MutabilityTier
from ..models import PriorityTag, Proposal
from ..speaker import SpeakerStateMachine
from ..tee.watchdog import DeadlockBreaker


class LeanStatus(str, Enum):
    """What the Lean corpus in ``gov-budget-proof/`` says about a prediction.

    The four values are exhaustive over :data:`LEAN_COVERAGE` and are rendered
    verbatim in the coverage table of ``book/formal-verification-lean.md``.

    Even :attr:`THEOREM` claims nothing about ``src/nomos/``: the theorem is
    proved of a Lean model that nothing extracts from the Python, so the two
    can drift apart without any check noticing. See the scope note in
    ``book/formal-verification-lean.md``.
    """

    THEOREM = "proved of the Lean model"
    DIFFERENT_ENCODING = "modelled under a different encoding"
    MODELLED_ONLY = "modelled, no theorem"
    NO_COUNTERPART = "no counterpart"


@dataclass(frozen=True)
class LeanCoverage:
    """How one prediction relates to the Lean corpus.

    Attributes:
        status: Which of the four :class:`LeanStatus` cases this row is.
        declarations: Lean declarations this prediction corresponds to, named
            exactly as ``gov-budget-proof/`` declares them. For
            :attr:`LeanStatus.THEOREM` and
            :attr:`LeanStatus.DIFFERENT_ENCODING` these are theorems; for
            :attr:`LeanStatus.MODELLED_ONLY` they are the definitions that
            model the same object without a theorem stating the claim.
        note: What the correspondence is and is not worth, in prose.

    Editing convention: ``note`` names no Lean declaration that is absent from
    ``declarations``, because ``declarations`` is the part
    ``tests/test_lean_claims.py`` checks against the corpus. A name carried
    only in the prose is a name nothing would catch going stale.
    """

    status: LeanStatus
    declarations: tuple[str, ...]
    note: str


LEAN_COVERAGE: dict[int, LeanCoverage] = {
    1: LeanCoverage(
        status=LeanStatus.THEOREM,
        declarations=("budget_invariant_holds", "budget_never_exceeded"),
        note=(
            "BudgetEnforcement.lean caps a per-member count the same way "
            "set_agenda does: processing a cycle never lets a member's used "
            "count exceed their budget, from any state that already satisfies "
            "the invariant, and the corollary specialises that to the empty "
            "initial state this test starts from. The kappa-2 budget is a Nat "
            "count in the model and an int count in the implementation, so "
            "this row is not type-mismatched -- only unlinked."
        ),
    ),
    2: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "The corpus has no priority tag and no agenda order: a "
            "case-insensitive search for 'priority' over gov-budget-proof/ "
            "matches nothing, and no declaration sorts proposals."
        ),
    ),
    3: LeanCoverage(
        status=LeanStatus.MODELLED_ONLY,
        declarations=("weightedSum", "totalWeight", "thresholdOf", "votePasses"),
        note=(
            "VoteAndFalsification.lean models the vote itself, and its routine "
            "threshold of 1/2 is the 0.5 majority_threshold default of "
            "SpeakerStateMachine. But the equivalence this test asserts -- "
            "consensus exactly when the weighted average clears the threshold "
            "-- is that definition rather than a theorem about it. What the "
            "corpus proves of the vote is that the outcome depends only on the "
            "tallies and that it is decided by computation, neither of which "
            "is this claim."
        ),
    ),
    4: LeanCoverage(
        status=LeanStatus.THEOREM,
        declarations=(
            "budget_halving_formula",
            "budget_unchanged_below_cutoff",
            "budget_preserves_positive",
        ),
        note=(
            "The cutoff is 3 falsifications in both models, and the Lean "
            "theorems pin the new budget at max 1 (old / 2) at or above it and "
            "at the old value below it -- strictly more than this test "
            "asserts, which is only that the budget fell. What triggers the "
            "halving is encoded differently: Lean thresholds a Nat integrity "
            "score, the Python drives it with a float identity_coherence. The "
            "budget arithmetic downstream of the trigger is a count on both "
            "sides."
        ),
    ),
    5: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "No Ulysses contract in the corpus. A case-insensitive search for "
            "'restrict' over gov-budget-proof/ matches nothing, and no "
            "declaration models an action set a contract removes members from."
        ),
    ),
    6: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "Nothing models enactment or revocation thresholds: a "
            "case-insensitive search for 'revocation' over gov-budget-proof/ "
            "matches nothing. IdentityTiers.lean orders quorum bars across "
            "tiers, which is a different ordering than revocation above "
            "enactment within one contract."
        ),
    ),
    7: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "No timelock and no contract state machine: a case-insensitive "
            "search for 'timelock' over gov-budget-proof/ matches nothing. The "
            "cooldown in IdentityTiers.lean is a cooling-off bar on identity "
            "changes, not the kappa-3 unlock cycle this test steps a contract "
            "through."
        ),
    ),
    8: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "No mask composition in the corpus: a case-insensitive search for "
            "'mask' over gov-budget-proof/ matches nothing, and no declaration "
            "takes a difference of two action sets."
        ),
    ),
    9: LeanCoverage(
        status=LeanStatus.DIFFERENT_ENCODING,
        declarations=(
            "acceptable_iff_ge",
            "below_threshold_rejection_leaves_state",
            "rejected_action_does_not_mutate_identity",
        ),
        note=(
            "IdentityCoherence.lean gates on a Nat coherence score against a "
            "threshold of 70 on a 0-100 scale, and proves that a "
            "below-threshold action leaves identity state untouched. This test "
            "passes an identity_coherence of 0.1 on a 0.0-1.0 scale and "
            "asserts a different consequent: that the cycle defaulted, or that "
            "the integrity member scored below 0.8. Neither the scale nor the "
            "conclusion is shared."
        ),
    ),
    10: LeanCoverage(
        status=LeanStatus.DIFFERENT_ENCODING,
        declarations=(
            "constitutional_requires_quorum_and_cooldown",
            "constitutional_change_meets_genesis_bar",
            "dynamic_requires_only_majority",
        ),
        note=(
            "IdentityTiers.lean states the constitutional bar as numbers -- at "
            "least 3 signatures and at least 30 days -- and derives that any "
            "permitted constitutional change carries at least the genesis "
            "quorum, which is as close as the corpus comes to 'requires "
            "external multisig'. This test reads a bool flag on TIER_RULES "
            "instead, and the Lean model has no such flag. The TierRule "
            "records it indexes do carry a cooling_off_days at the same "
            "numbers the Lean model uses -- 30 days constitutional, 7 "
            "operational -- and a modification_threshold string naming the "
            "same 3-of-5 multisig, but the test asserts neither and nothing "
            "ties either to the model, so the theorem and the assert are "
            "still not two statements of one claim."
        ),
    ),
    11: LeanCoverage(
        status=LeanStatus.THEOREM,
        declarations=(
            "two_signatures_insufficient",
            "three_signatures_sufficient",
            "double_signing_cannot_reach_quorum_alone",
            "quorumCount_bounded_by_five",
        ),
        note=(
            "The closest correspondence in the repo: both sides count distinct "
            "signers against a 3-of-5 bar. The two-signature, three-signature "
            "and one-principal-signing-repeatedly clauses of this test each "
            "have a theorem beside them, and the fixed five-key set the fourth "
            "theorem bounds is the model's version of the holder cap. The two "
            "registration clauses -- a sixth holder and a repeat holder both "
            "refused -- are properties of the Python API, which the Lean model "
            "does not have. tests/test_keys.py checks the same quorum property "
            "of GenesisMultisig by hand: a second Python test, not a link."
        ),
    ),
    12: LeanCoverage(
        status=LeanStatus.NO_COUNTERPART,
        declarations=(),
        note=(
            "No watchdog and no deadlock breaker in the corpus: a "
            "case-insensitive search for 'deadlock' over gov-budget-proof/ "
            "matches nothing."
        ),
    ),
}
"""Prediction-to-Lean correspondence, re-derived against the current corpus.

Keyed by prediction id. This is the source the coverage table in
``book/formal-verification-lean.md`` renders, and ``tests/test_lean_claims.py``
fails if any name here is not declared in ``gov-budget-proof/``.

Read it as a map between two artefacts that are not connected: the predictions
are Python asserts over ``src/nomos/``, the theorems are proved of Lean models,
and nothing checks that the two describe the same system.
"""


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

    @property
    def lean(self) -> LeanCoverage | None:
        """This prediction's row in :data:`LEAN_COVERAGE`, or ``None``.

        ``None`` only for an id outside 1-12, which
        :func:`nomos.prove.runner.run_all` never produces.
        """
        return LEAN_COVERAGE.get(self.id)


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
    locked_at_enactment = contract.state == ContractState.ENACTED and contract.unlock_at_cycle == 10
    for _ in range(5):
        contract.tick()
    mid = enforce_timelock(contract, contract.current_cycle)
    still_enacted = contract.state == ContractState.ENACTED
    for _ in range(5):
        contract.tick()
    elapsed = enforce_timelock(contract, contract.current_cycle)
    activated = contract.state == ContractState.ACTIVE
    duration_unchanged = contract.timelock_blocks == 10
    passed = (
        locked_at_enactment
        and mid.compliant
        and still_enacted
        and not elapsed.compliant
        and activated
        and duration_unchanged
    )
    return PredictionResult(
        id=7,
        chapter="Ch3",
        section="2.4",
        description="Timelock holds until its unlock cycle, blocking early revocation",
        passed=passed,
        evidence=f"Enacted at cycle 0 with timelock_blocks=10 -> unlock_at_cycle={contract.unlock_at_cycle}; at cycle 5: {mid.reason} state={'ENACTED' if still_enacted else contract.state.name}; at cycle 10: {elapsed.reason} state={contract.state.name}; timelock_blocks still {contract.timelock_blocks}",
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

    # Three distinct signatures is the happy path, but it is the only path the
    # model and the implementation ever agreed on. The quorum is only really
    # 3-of-5 if the negative cases hold too: n is capped, and one principal
    # cannot register (and therefore sign) more than once.
    try:
        ms.add_holder("frank")
        cap_enforced = False
    except ValueError:
        cap_enforced = True

    solo = GenesisMultisig(threshold=3, total_holders=5)
    dup_rejected = True
    for i in range(3):
        try:
            solo.add_holder("mallory")
        except ValueError:
            if i == 0:  # the first registration must succeed
                dup_rejected = False
        else:
            if i > 0:  # every repeat must be refused
                dup_rejected = False
    for _ in range(3):
        solo.sign("mallory")
    solo_blocked = not solo.is_authorized

    passed = not not_yet and authorized and cap_enforced and dup_rejected and solo_blocked
    return PredictionResult(
        id=11,
        chapter="Ch4",
        section="3.1",
        description=(
            "Genesis 3-of-5 multisig: 2 sigs insufficient, 3 sigs authorizes, "
            "n capped, and one principal cannot reach quorum alone"
        ),
        passed=passed,
        evidence=(
            f"Sigs=2 authorized={not_yet}, Sigs=3 authorized={authorized}, "
            f"6th holder refused={cap_enforced}, duplicate refused={dup_rejected}, "
            f"one principal signing 3x authorized={not solo_blocked}"
        ),
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
