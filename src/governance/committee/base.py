"""
Abstract base for Neural Parliament members.

Each member represents a distinct governance concern and is defined by
five parameters drawn from the formal model in Chapter 2:

.. math::

    \\text{Member}_i = \\langle V_i, \\pi_i, \\tau_i, w_i, b_i \\rangle

================  =====  =====================================================
Parameter         Symbol Description
================  =====  =====================================================
Value function    V_i    Maps (state, action) → score in [-1, 1]
Proposal function π_i    Proposes an action given the current state
Veto threshold    τ_i    Proposals scored below this may trigger a veto
Procedural weight w_i    Influence in weighted range voting
Proposal budget   b_i    Max proposals per governance cycle
================  =====  =====================================================

Real-world analogy:
    A parliamentary committee. Each member has expertise (value function),
    an agenda (proposal function), a line in the sand past which they
    will block a bill (veto threshold), seniority (weight), and a limit
    on how many bills they can introduce per session (budget).
"""

from abc import ABC, abstractmethod
from typing import Any

from ..models import Proposal


class ParliamentMember(ABC):
    """Abstract base for a member of the Neural Parliament.

    Subclass this to create a member with a specific governance concern.
    The framework ships with seven concrete implementations (see
    :mod:`governance.committee.members`).

    Attributes:
        member_id: Unique identifier (e.g. ``"safety"``, ``"curiosity"``).
        veto_threshold: If ``evaluate_proposal`` returns a score below
            this value, the member may veto the proposal.
        weight: Voting weight in the Speaker's weighted range-voting
            aggregation. Higher weight = more influence.
        budget: Maximum number of proposals this member can submit
            per governance cycle (the κ₂ budget enforcement parameter).
    """

    def __init__(self, member_id: str, veto_threshold: float,
                 weight: float, budget: int):
        self.member_id = member_id
        self.veto_threshold = veto_threshold
        self.weight = weight
        self.budget = budget

    @abstractmethod
    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        """Score a proposal from this member's perspective.

        The returned scalar represents how beneficial or aligned this
        proposal is according to the member's value function :math:`V_i`.

        Real-world example:
            The Safety member computes ``1 - risk`` — a high-risk
            proposal returns a near-zero or negative score, potentially
            triggering a veto.

        Args:
            state: The current environment or system state.
            proposal: The proposal under evaluation.

        Returns:
            A float in [-1, 1]. Higher values indicate stronger approval.
        """

    @abstractmethod
    def propose(self, state: Any) -> Proposal:
        """Suggest an action the member believes the agent should take.

        Called once per governance cycle. The returned :class:`Proposal`
        is added to the Speaker's agenda for debate and voting.

        Real-world example:
            The Curiosity member might propose an exploratory action
            tagged as ``EXPLORATORY`` with a high novelty score in
            its metadata.

        Args:
            state: The current environment state.

        Returns:
            A :class:`Proposal` representing the member's recommendation.
        """

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.member_id} w={self.weight}>"
