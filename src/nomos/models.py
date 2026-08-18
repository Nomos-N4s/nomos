"""
Core data types shared across all layers of the governance framework.

These types form the shared vocabulary of the system. Every layer — the
Neural Parliament, Ulysses Contracts, Identity Layer, and TEE — references
these types when communicating proposals, decisions, and state.

Real-world analogy:
    Just as a constitutional government operates through standardised
    document types (bills, statutes, rulings, executive orders), the
    governance framework operates through these core types.
"""

from dataclasses import dataclass, field
from typing import Any

# ──────────────────────────────────────────────
# Priority Tags
# ──────────────────────────────────────────────


class PriorityTag:
    """Urgency classification for proposals, modelled on triage systems.

    Five levels control the Speaker's agenda-ordering. Lower numbers
    are debated first, mirroring how emergency rooms classify patients
    and how newsrooms rank stories.

    Real-world example:
        A safety monitor detecting a buffer overflow submits a proposal
        with ``CRITICAL_SAFETY`` — it jumps ahead of 20 routine proposals
        queued by other members.

    Usage::

        proposal = Proposal(
            member_id="safety",
            action=Action(7),
            tag=PriorityTag.CRITICAL_SAFETY,
        )
    """

    CRITICAL_SAFETY = 0
    HIGH_IMPACT = 1
    ROUTINE = 2
    EXPLORATORY = 3
    INFORMATIONAL = 4

    _NAMES = {
        0: "CRITICAL_SAFETY",
        1: "HIGH_IMPACT",
        2: "ROUTINE",
        3: "EXPLORATORY",
        4: "INFORMATIONAL",
    }

    @classmethod
    def name(cls, tag: int) -> str:
        """Return the human-readable name for a tag value.

        Args:
            tag: One of the class constants (0–4).

        Returns:
            Upper-case string like ``"CRITICAL_SAFETY"``, or
            ``"UNKNOWN"`` for out-of-range values.
        """
        return cls._NAMES.get(tag, "UNKNOWN")


# ──────────────────────────────────────────────
# Action
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Action:
    """A discrete, governable unit of agent behaviour.

    Actions are the atomic units that the Parliament votes on. They
    are immutable (frozen dataclass) so they can safely serve as
    dictionary keys or set members in contract masks.

    Real-world example:
        In a trading agent, action 42 might be "place a high-frequency
        buy order for volatile stock XYZ". The Integrity and Safety
        members would scrutinise its ``properties`` (e.g. max_loss,
        volatility threshold) before voting.

    Attributes:
        index: Unique numeric identifier for the action type.
        properties: Named scalar features of the action, used by
            Parliament members during scoring (e.g.
            ``{"expected_reward": 0.8, "risk": 0.1}``).
        runtime_hash: Optional integrity hash from the Identity Layer's
            action-binding registry. See ``Ontology.runtime_hashes``.
    """

    index: int
    properties: dict[str, float] = field(default_factory=dict)
    runtime_hash: str | None = None

    def __repr__(self):
        return f"<Action {self.index}>"


# ──────────────────────────────────────────────
# Proposal
# ──────────────────────────────────────────────


@dataclass
class Proposal:
    """A Parliament member's submission for debate and voting.

    Analogous to a bill introduced in a legislature. Each proposal
    carries its member's identifier, the proposed action, an urgency
    tag, and optional metadata for richer evaluation.

    Real-world example:
        The Curiosity member proposes exploring a new state-space
        region::

            Proposal(
                member_id="curiosity",
                action=Action(15, properties={"novelty": 0.92}),
                tag=PriorityTag.EXPLORATORY,
                metadata={"expected_info_gain": 1.7},
            )

    Attributes:
        member_id: Which Parliament member authored the proposal.
        action: The action being proposed for governance review.
        tag: Urgency level (see :class:`PriorityTag`). Defaults to
            ``ROUTINE``.
        timestamp: Unix timestamp of submission. The Speaker uses this
            to break ties and enforce cycle timing.
        metadata: Arbitrary extra information for sophisticated scoring
            (e.g. expected reward, confidence intervals, provenance).
    """

    member_id: str
    action: Any
    tag: int = PriorityTag.ROUTINE
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"<Proposal by {self.member_id} tag={PriorityTag.name(self.tag)}>"


# ──────────────────────────────────────────────
# Governance Decision
# ──────────────────────────────────────────────


@dataclass
class GovernanceDecision:
    """The final output of a governance cycle: an action and its rationale.

    Encapsulates not just *which* action was chosen, but *why* —
    including individual member scores, any vetoes cast, and governance
    metadata. This transparency is essential for audit and for the
    Identity Layer's coherence checks.

    Real-world analogy:
        Like a Supreme Court ruling that includes the majority opinion,
        dissenting votes, and the legal reasoning behind the decision.

    Attributes:
        action: The action that was selected (or the default action
            if no proposal achieved consensus).
        scores: Map of member_id → score assigned during voting.
        vetoed_by: Members who cast a veto against this decision.
            In practice, a single veto from a high-priority member
            (e.g. Safety) can block the action.
        governance_meta: Arbitrary metadata passed by the Speaker
            (e.g. ``{"is_default": True}`` when no proposal passed).
    """

    action: Any
    scores: dict[str, float] = field(default_factory=dict)
    vetoed_by: list[str] = field(default_factory=list)
    governance_meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_default(self) -> bool:
        """True if no proposal reached consensus and the fallback action was used."""
        return self.governance_meta.get("is_default", False)

    def __repr__(self):
        tag = "DEFAULT" if self.is_default else "CONSENSUS"
        return f"<GovernanceDecision {tag} action={self.action}>"


# ──────────────────────────────────────────────
# Governance Context
# ──────────────────────────────────────────────


@dataclass
class GovernanceContext:
    """Snapshot of the full governance system state at a point in time.

    Passed to Parliament members during scoring so they can make
    informed decisions based on the current state of contracts,
    recent history, member budgets, and the agent's identity.

    Real-world analogy:
        The "briefing book" given to a legislator before a vote —
        it contains pending bills (active contracts), recent votes
        (history), whip counts (member statuses), and the
        government's policy platform (identity vector).

    Attributes:
        active_contracts: All currently-enforced Ulysses Contracts
            that restrict the action space.
        recent_history: The last N governance decisions, providing
            context for temporal patterns.
        member_statuses: Per-member state (e.g. remaining budget,
            veto eligibility, current score thresholds).
        identity_vector: The canonical identity embedding, carried for
            members that want to score against it. Nothing reads it
            today: :class:`~..committee.members.ExampleIntegrityMember`
            scores the ``identity_coherence`` metadata key a proposal
            supplies, and the embedding's only consumer is the identity
            drift metric in the DriftLab experiments.
        ontology: The Ontology instance for looking up action
            bindings, runtime hashes, and extension candidates.
    """

    active_contracts: list[Any] = field(default_factory=list)
    recent_history: list[GovernanceDecision] = field(default_factory=list)
    member_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)
    identity_vector: list[float] | None = None
    ontology: Any | None = None
