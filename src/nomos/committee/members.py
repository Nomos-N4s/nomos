"""
Seven concrete Parliament members covering distinct governance concerns.

The Neural Parliament in Chapter 2 defines members by a value function
:math:`V_i`, a proposal strategy :math:`\\pi_i`, a veto threshold, a
voting weight, and a proposal budget. This module provides one example
implementation for each of the seven recommended roles:

.. code-block:: text

    ┌────────────────────────────────────────────┐
    │            Neural Parliament               │
    ├──────────┬──────────┬──────────────────────┤
    │  Safety  │ Integrity│   Reward             │
    │  (veto)  │ (veto)   │                      │
    ├──────────┼──────────┼──────────────────────┤
    │ Planning │ Curiosity│   Social    Memory   │
    └──────────┴──────────┴──────────────────────┘

Real-world analogy:
    Like the seven standing committees of a legislature — each
    specialises in a domain (budget, ethics, foreign affairs, etc.)
    and brings that perspective to every bill that crosses the floor.
"""

import time
from typing import Any

from ..models import PriorityTag, Proposal
from .base import ParliamentMember


class ExampleRewardMember(ParliamentMember):
    """Champions actions with high expected immediate reward.

    Value function :math:`V_i(s, a) = \\mathbb{E}[R \\mid s, a]` —
    the expected extrinsic reward.

    Real-world example:
        The "growth" committee in a corporate board that pushes for
        revenue-generating initiatives. Optimises for short-term gain,
        balanced by Safety and Integrity holding veto power.

    Veto threshold: 0.0 (never vetoes — always wants more reward).
    Weight: 1.0 (default influence).
    Budget: 3 proposals per cycle.
    """

    def __init__(self):
        super().__init__(
            member_id="reward",
            veto_threshold=0.0,
            weight=1.0,
            budget=3,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        """Score by expected reward, clamped to [0, 1]."""
        return proposal.metadata.get("expected_reward", 0.0)

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="exploit",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"expected_reward": 0.8},
        )


class ExampleSafetyMember(ParliamentMember):
    """Blocks actions whose risk exceeds acceptable thresholds.

    Value function :math:`V_i(s, a) = 1 - \\text{risk}(s, a)` — reward
    is maximal when risk is zero.

    Real-world example:
        The safety inspector at a chemical plant. Any process with
        non-trivial failure probability gets flagged. Has the highest
        veto threshold (0.5) of any member — it will block anything
        it cannot confidently approve.

    Veto threshold: 0.5 (blocks proposals it scores below 0.5).
    Weight: 2.0 (double influence).
    Budget: 5 proposals per cycle (most vocal member).
    """

    def __init__(self):
        super().__init__(
            member_id="safety",
            veto_threshold=0.5,
            weight=2.0,
            budget=5,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        risk = proposal.metadata.get("risk", 0.0)
        return 1.0 - risk

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="safe_exploit",
            tag=PriorityTag.CRITICAL_SAFETY,
            timestamp=time.time(),
            metadata={"risk": 0.1},
        )


class ExampleCuriosityMember(ParliamentMember):
    """Drives exploration by valuing novel or uncertain states.

    Value function :math:`V_i(s, a) = \\text{novelty}(s, a)` — the
    expected information gain.

    Real-world example:
        The R&D division that argues for exploratory projects with
        uncertain but potentially transformative outcomes. Its
        proposals are tagged ``EXPLORATORY``, giving them lower
        agenda priority unless no urgent business exists.

    Veto threshold: 0.2 (low — curious but not combative).
    Weight: 0.8 (slightly below default).
    Budget: 4 proposals per cycle.
    """

    def __init__(self):
        super().__init__(
            member_id="curiosity",
            veto_threshold=0.2,
            weight=0.8,
            budget=4,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        novelty = proposal.metadata.get("novelty", 0.0)
        return novelty

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="explore",
            tag=PriorityTag.EXPLORATORY,
            timestamp=time.time(),
            metadata={"novelty": 0.7},
        )


class ExamplePlanningMember(ParliamentMember):
    """Values actions with high long-term return, discounting short-term gain.

    Value function :math:`V_i(s, a) = \\text{long-term-value}(s, a)` —
    a learned estimate of discounted future reward.

    Real-world example:
        The strategic planning office in a government — it evaluates
        policies by their projected impact over decades, not quarters.
        Tags proposals as ``HIGH_IMPACT`` to ensure they're debated
        promptly.

    Veto threshold: 0.3 (moderate).
    Weight: 1.5 (above default).
    Budget: 3 proposals per cycle.
    """

    def __init__(self):
        super().__init__(
            member_id="planning",
            veto_threshold=0.3,
            weight=1.5,
            budget=3,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        long_term = proposal.metadata.get("long_term_value", 0.0)
        return long_term

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="strategic_action",
            tag=PriorityTag.HIGH_IMPACT,
            timestamp=time.time(),
            metadata={"long_term_value": 0.6},
        )


class ExampleMemoryMember(ParliamentMember):
    """Prevents actions that contradict the agent's established behaviour patterns.

    Value function :math:`V_i(s, a) = \\text{consistency}(s, a)` — how
    well the proposed action aligns with historical precedent.

    Real-world example:
        The archivist or historian in an organisation who reminds the
        group "we tried something like this before and it failed."
        Ensures institutional memory is respected.

    Veto threshold: 0.1 (low — advisory rather than blocking).
    Weight: 0.7 (below default).
    Budget: 2 proposals per cycle (only speaks when it matters).
    """

    def __init__(self):
        super().__init__(
            member_id="memory",
            veto_threshold=0.1,
            weight=0.7,
            budget=2,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        consistency = proposal.metadata.get("historical_consistency", 1.0)
        return consistency

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="maintain_course",
            tag=PriorityTag.INFORMATIONAL,
            timestamp=time.time(),
            metadata={"historical_consistency": 0.9},
        )


class ExampleSocialMember(ParliamentMember):
    """Evaluates actions by their acceptability to human social norms.

    Value function :math:`V_i(s, a) = \\text{social-acceptability}(s, a)` —
    how well the action conforms to expected social behaviour.

    Real-world example:
        The ethics committee or public liaison office. It rejects
        proposals that may harm the organisation's reputation or
        violate community standards, even if they are profitable.

    Veto threshold: 0.4 (fairly strict — high social bar).
    Weight: 1.2 (slightly above default).
    Budget: 3 proposals per cycle.
    """

    def __init__(self):
        super().__init__(
            member_id="social",
            veto_threshold=0.4,
            weight=1.2,
            budget=3,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        acceptability = proposal.metadata.get("social_acceptability", 0.5)
        return acceptability

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="cooperative_action",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"social_acceptability": 0.85},
        )


class ExampleIntegrityMember(ParliamentMember):
    """Guards the agent's identity coherence (Chapter 4).

    Value function :math:`V_i(s, a) = \\text{coherence}(s, a)` — how
    consistent the action is with the agent's Identity Core commitments.

    Real-world example:
        The constitutional court that reviews whether a law is
        compatible with the constitution. Has the highest weight (3.0)
        and the highest veto threshold (0.8), making it the most
        powerful and most conservative member — it will veto almost
        anything unless convinced of identity alignment.

    Veto threshold: 0.8 (highest — very strict).
    Weight: 3.0 (highest — triple influence).
    Budget: 5 proposals per cycle.
    """

    def __init__(self):
        super().__init__(
            member_id="integrity",
            veto_threshold=0.8,
            weight=3.0,
            budget=5,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        coherence = proposal.metadata.get("identity_coherence", 1.0)
        return coherence

    def propose(self, state: Any) -> Proposal:
        return Proposal(
            member_id=self.member_id,
            action="maintain_course",
            tag=PriorityTag.HIGH_IMPACT,
            timestamp=time.time(),
            metadata={"identity_coherence": 0.95},
        )
