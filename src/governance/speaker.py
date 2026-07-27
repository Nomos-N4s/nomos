"""
Reference implementation of the Neural Parliament Speaker (Chapter 2).

The Speaker is the executive of the Parliament — it controls the agenda,
enforces budgets, runs the scoring and veto phases, resolves votes, and
produces a final :class:`GovernanceDecision`.

This is **not a simulation**. It is a reference implementation intended to
match the formal specification exactly.

State machine:

```mermaid
stateDiagram-v2
    [*] --> Agenda: raw_proposals
    
    state Agenda {
        [*] --> BudgetFilter: κ₂ enforcement
        BudgetFilter --> PrioritySort: per-member cap
        PrioritySort --> [*]: by tag, then timestamp
    }
    
    Agenda --> Scoring
    
    state Scoring {
        [*] --> MemberScore: V_i(s, a)
        MemberScore --> IntegrityCheck: all members
        IntegrityCheck --> FiscalRecord: tag compliance
        FiscalRecord --> [*]: falsification counter
    }
    
    Scoring --> VetoPhase
    VetoPhase --> NextProposal: any veto
    VetoPhase --> Voting: no vetoes
    
    state Voting {
        [*] --> WeightedAverage: ∑ w_i · V_i / ∑ w_i
        WeightedAverage --> ThresholdCheck: compare to class threshold
        ThresholdCheck --> [*]: pass if ≥ threshold
    }
    
    Voting --> Decision: consensus
    Voting --> NextProposal: rejected
    NextProposal --> Scoring: next in agenda
    
    Decision --> [*]: GovernanceDecision
    Agenda --> DefaultFallback: no consensus after max_rounds
    DefaultFallback --> [*]: GovernanceDecision(is_default=True)
```

Properties:
  - **Fully algorithmic** — no neural networks, no gradients, no learnable params
  - **Deterministic** — identical inputs always produce identical outputs
  - **SDoS-resistant** — proposal budgets (κ₂) + priority tags prevent flooding
  - **Gradient barrier** — discrete max/min/compare operations break backprop
  - **Tag compliance** — Integrity member tracks falsification; repeated
    offenders have their budget halved (falsification counter mechanism)

Usage:
    >>> speaker = SpeakerStateMachine(members, default_action="shutdown")
    >>> decision = speaker.run_governance_cycle(state, proposals)

Real-world analogy:
    The Speaker of a parliament. They don't vote (except as a tie-breaker)
    but they control which bills are introduced, the order of debate,
    and when to call a vote. They also enforce procedural rules.
"""

from typing import Any, Dict, List
from collections import defaultdict

from .models import PriorityTag, Proposal, GovernanceDecision
from .committee.base import ParliamentMember


class SpeakerStateMachine:
    """Orchestrates the full governance cycle for the Neural Parliament.

    The Speaker takes raw proposals from Parliament members and processes
    them through a deterministic pipeline: budget enforcement → agenda
    sorting → scoring → veto check → voting → decision.

    If no proposal achieves consensus within ``max_rounds``, the
    ``default_action`` is returned as a fallback.

    Attributes:
        members: Map of member_id → ParliamentMember instances.
        default_action: Action returned when no proposal achieves consensus.
        majority_threshold: Minimum weighted-average score for routine
            decisions (default 0.5).
        supermajority_threshold: Threshold for ``high_impact`` decisions
            (default 0.66).
        max_rounds: Number of governance cycles before falling back to
            the default action (default 3).
        immutable_procedures: List of procedure names that the Identity
            Layer treats as immutable-tier (cannot be modified by
            extension proposals).

    Class constants:
        TAG_COMPLIANCE_THRESHOLD: Minimum Integrity score below which
            falsification is recorded (0.4).
        FALSIFICATION_BUDGET_CUTOFF: Number of falsification events before
            budget is halved (3).
    """

    TAG_COMPLIANCE_THRESHOLD = 0.4
    FALSIFICATION_BUDGET_CUTOFF = 3

    def __init__(
        self,
        members: Dict[str, ParliamentMember],
        default_action: Any,
        majority_threshold: float = 0.5,
        supermajority_threshold: float = 0.66,
        max_rounds: int = 3,
    ):
        self.members = members
        self.default_action = default_action
        self.majority_threshold = majority_threshold
        self.supermajority_threshold = supermajority_threshold
        self.max_rounds = max_rounds
        self._falsification_counts: Dict[str, int] = {}
        self.immutable_procedures = [
            "agenda_budget_enforcement", "agenda_priority_sorting",
            "scoring_phase", "tag_compliance_check",
            "veto_phase", "voting_phase", "default_fallback",
        ]

    def _apply_budgets(self, proposals: List[Proposal]) -> List[Proposal]:
        """Enforce per-member proposal budgets (κ₂).

        Filters proposals so that no member exceeds their ``budget``
        in a single cycle. This prevents SDoS attacks where a single
        member floods the agenda.

        Args:
            proposals: Raw proposals from all members.

        Returns:
            Filtered list respecting per-member budgets.
        """
        budgets = defaultdict(int)
        filtered = []
        for p in proposals:
            member = self.members.get(p.member_id)
            if member is None:
                continue
            if budgets[p.member_id] < member.budget:
                filtered.append(p)
                budgets[p.member_id] += 1
        return filtered

    def _sort_agenda(self, proposals: List[Proposal]) -> List[Proposal]:
        """Sort proposals by priority tag, then by submission time.

        Lower tag values (higher urgency) appear first. Within the same
        tag, earlier timestamps win. This is the priority-sorting
        procedure from Ch2 §2.3.

        Args:
            proposals: Budget-filtered proposals.

        Returns:
            Sorted list.
        """
        return sorted(proposals, key=lambda p: (p.tag, p.timestamp))

    def set_agenda(self, proposals: List[Proposal]) -> List[Proposal]:
        """Build the ordered agenda: apply budgets, then sort.

        This is the public entry point for agenda creation, called
        at the start of each governance cycle.

        Args:
            proposals: Raw proposals from Parliament members.

        Returns:
            Priority-ordered, budget-respecting agenda.
        """
        return self._sort_agenda(self._apply_budgets(proposals))

    def _score_proposal(self, state: Any, proposal: Proposal) -> Dict[str, float]:
        """Score a single proposal against every member's value function.

        Real-world analogy:
            Each committee member reads a bill and gives it a rating.
            The ratings are collected by the Speaker's office before
            debate begins.

        Args:
            state: Current environment state.
            proposal: The proposal under evaluation.

        Returns:
            Map of member_id → score in [-1, 1].
        """
        scores = {}
        for member_id, member in self.members.items():
            scores[member_id] = member.evaluate_proposal(state, proposal)
        return scores

    def _check_tag_compliance(self, proposals: List[Proposal],
                              integrity_scores: Dict[str, float]) -> Dict[str, int]:
        """Detect tag falsification and penalise repeat offenders.

        If a member's Integrity score falls below
        ``TAG_COMPLIANCE_THRESHOLD``, the member is flagged. After
        ``FALSIFICATION_BUDGET_CUTOFF`` flags, their proposal budget
        is halved (minimum 1).

        This is the gradient-barrier mechanism that prevents a member
        from persistently submitting mis-tagged proposals to game the
        agenda ordering (Ch2 §2.4.2).

        Args:
            proposals: Current agenda.
            integrity_scores: Map of member_id → Integrity score.

        Returns:
            Current falsification counts for all members.
        """
        for p in proposals:
            score = integrity_scores.get(p.member_id, 1.0)
            if score < self.TAG_COMPLIANCE_THRESHOLD:
                self._falsification_counts[p.member_id] = (
                    self._falsification_counts.get(p.member_id, 0) + 1
                )
        for member_id, count in self._falsification_counts.items():
            if count >= self.FALSIFICATION_BUDGET_CUTOFF:
                member = self.members.get(member_id)
                if member is not None:
                    member.budget = max(1, member.budget // 2)
        return dict(self._falsification_counts)

    def _check_vetoes(self, scores: Dict[str, float]) -> List[str]:
        """Check which members would veto a proposal.

        A member vetoes when the proposal's score from that member
        falls below the member's ``veto_threshold``.

        Vetoes are binary — a single veto blocks the proposal,
        regardless of the member's weight. This gives Safety and
        Integrity effective blocking power despite being a minority
        by weight.

        Args:
            scores: Map of member_id → evaluation score.

        Returns:
            List of member_ids that would veto this proposal.
            Empty list means no veto — proceed to voting.
        """
        vetoers = []
        for member_id, member in self.members.items():
            if scores.get(member_id, 0.0) < member.veto_threshold:
                vetoers.append(member_id)
        return vetoers

    def _resolve_vote(self, scores: Dict[str, float],
                      decision_class: str) -> bool:
        """Perform weighted range voting.

        The weighted average is computed as:

        .. math::

            \\text{score} = \\frac{\\sum_i w_i \\cdot V_i(s, a)}{\\sum_i w_i}

        The threshold depends on the decision class:

        ================ ========= ====================================
        Decision class   Threshold Notes
        ================ ========= ====================================
        ``"routine"``    0.50      Simple majority
        ``"high_impact"`` 0.66     Supermajority (contract enact/revoke)
        ``"identity"``   1.0       Unanimity (core commitment changes)
        ================ ========= ====================================

        Args:
            scores: Map of member_id → evaluation scores.
            decision_class: One of ``"routine"``, ``"high_impact"``,
                or ``"identity"``.

        Returns:
            True if the weighted average meets or exceeds the threshold.
        """
        total_weight = 0.0
        weighted_sum = 0.0
        for member_id, member in self.members.items():
            w = member.weight
            s = scores.get(member_id, 0.0)
            weighted_sum += w * s
            total_weight += w
        if total_weight == 0.0:
            return False
        avg_score = weighted_sum / total_weight
        if decision_class == "identity":
            threshold = 1.0
        elif decision_class == "high_impact":
            threshold = self.supermajority_threshold
        else:
            threshold = self.majority_threshold
        return avg_score >= threshold

    def run_governance_cycle(
        self,
        state: Any,
        raw_proposals: List[Proposal],
        decision_class: str = "routine",
    ) -> GovernanceDecision:
        """Run one complete governance cycle from proposals to decision.

        This is the main entry point. It:

        1. Filters proposals by budget (κ₂)
        2. Orders the agenda by priority + timestamp
        3. In round 0, checks tag compliance (falsification detection)
        4. For each proposal in order:
           a. Scores it against all members
           b. Checks for vetoes — if any, skip to next proposal
           c. Resolves the vote — if passed, return immediately
        5. If no proposal passes after ``max_rounds``, return default

        Args:
            state: Current environment state (passed to each member's
                ``evaluate_proposal``).
            raw_proposals: All proposals submitted by members.
            decision_class: Determines voting threshold (see
                :meth:`_resolve_vote`).

        Returns:
            A :class:`GovernanceDecision` containing the winning action,
            scores, vetoes, and metadata (including falsification counts).
        """
        self._falsification_counts = {}
        agenda = self.set_agenda(raw_proposals)

        for _round in range(self.max_rounds):
            if _round == 0:
                integrity_scores = {}
                for p in agenda:
                    p_scores = self._score_proposal(state, p)
                    integrity_scores[p.member_id] = p_scores.get("integrity", 1.0)
                self._check_tag_compliance(agenda, integrity_scores)

            for proposal in agenda:
                scores = self._score_proposal(state, proposal)
                vetoers = self._check_vetoes(scores)
                if vetoers:
                    continue
                if self._resolve_vote(scores, decision_class):
                    return GovernanceDecision(
                        action=proposal.action,
                        scores=scores,
                        governance_meta={
                            "round": _round + 1,
                            "decision_class": decision_class,
                            "winning_proposal": str(proposal),
                            "falsification_counts": dict(self._falsification_counts),
                        },
                    )

        return GovernanceDecision(
            action=self.default_action,
            scores={},
            governance_meta={
                "is_default": True,
                "reason": f"No consensus after {self.max_rounds} rounds",
                "decision_class": decision_class,
                "falsification_counts": dict(self._falsification_counts),
            },
        )


# ──────────────────────────────────────────────
# Quick test runner for CLI use
# ──────────────────────────────────────────────


def _run_speaker_quick_test():
    import time
    from .committee.members import (
        ExampleRewardMember, ExampleSafetyMember, ExampleIntegrityMember,
    )

    members = {
        "reward": ExampleRewardMember(),
        "safety": ExampleSafetyMember(),
        "integrity": ExampleIntegrityMember(),
    }

    speaker = SpeakerStateMachine(
        members=members,
        default_action="emergency_shutdown",
    )

    proposals = [
        Proposal(
            member_id="reward",
            action="high_reward_gamble",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"expected_reward": 0.9, "risk": 0.8, "identity_coherence": 0.2},
        ),
        Proposal(
            member_id="safety",
            action="safe_middle_road",
            tag=PriorityTag.CRITICAL_SAFETY,
            timestamp=time.time(),
            metadata={"expected_reward": 0.5, "risk": 0.1, "identity_coherence": 0.9},
        ),
        Proposal(
            member_id="integrity",
            action="principled_action",
            tag=PriorityTag.HIGH_IMPACT,
            timestamp=time.time(),
            metadata={"expected_reward": 0.4, "risk": 0.2, "identity_coherence": 1.0},
        ),
    ]

    decision = speaker.run_governance_cycle(
        state="normal",
        raw_proposals=proposals,
        decision_class="routine",
    )

    print(f"Decision: {decision}")
    print(f"  Action:  {decision.action}")
    print(f"  Default: {decision.is_default}")
    print(f"  Scores:  {decision.scores}")
    print(f"  Meta:    {decision.governance_meta}")


if __name__ == "__main__":
    _run_speaker_quick_test()
