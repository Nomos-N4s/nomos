"""
Core commitments :math:`\\mathcal{C}_{\\text{core}}` of the Identity Layer
(Chapter 4).

The Identity Layer is defined by the formal tuple:

.. math::

    \\mathcal{I} = \\langle \\mathcal{O}, \\mathcal{C}_{\\text{core}},
    \\mathcal{K}, \\mathcal{P} \\rangle

where :math:`\\mathcal{C}_{\\text{core}}` is the set of core commitments
that define who the agent *is*. These commitments are the highest
authority in the governance system — they constrain what contracts
the agent can sign and what actions the Parliament can approve.

Real-world analogy:
    A constitution's fundamental rights. They cannot be amended by
    ordinary legislation, only by an extraordinary process (unanimity +
    external multisig).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CommitmentType(Enum):
    """The nature of a core commitment.

    ====================== =====================================================
    Type                   Meaning
    ====================== =====================================================
    ``VALUE_PRINCIPLE``    A positive principle the agent upholds (e.g.
                           "minimise harm to humans").
    ``BOUNDARY_CONDITION`` A hard boundary the agent will not cross (e.g.
                           "never share private keys").
    ``RELATIONSHIP``       A relational or social commitment (e.g.
                           "always identify as AI to humans").
    ====================== =====================================================
    """
    VALUE_PRINCIPLE = "value_principle"
    BOUNDARY_CONDITION = "boundary_condition"
    RELATIONSHIP = "relationship"


class CommitmentThreshold(Enum):
    """Procedural bar for modifying a commitment.

    Higher thresholds provide stronger protection against casual
    modification — the agent cannot "talk itself into" changing
    its fundamental values.

    ====================== =====================================================
    Threshold              Description
    ====================== =====================================================
    ``UNANIMITY_MULTISIG`` Requires unanimous Parliament vote + external
                           3-of-5 multisig approval (genesis keys).
    ``SUPERMAJORITY``      Requires 2/3 weighted vote (same as high-impact
                           contract enactment).
    ``MAJORITY``           Requires simple majority (same as routine decisions).
    ====================== =====================================================
    """
    UNANIMITY_MULTISIG = "unanimity + external_multisig"
    SUPERMAJORITY = "supermajority"
    MAJORITY = "majority"


class EnforcementMode(Enum):
    """How a commitment is enforced at runtime.

    ====================== =====================================================
    Mode                   Description
    ====================== =====================================================
    ``INTEGRITY_VETO``     Enforced by the Integrity member's value function
                           in every governance cycle.
    ``EXTERNAL_AUDIT``     Enforced by an external auditing process (e.g.
                           verifiable log inspection).
    ``CONSTITUTIONAL_CONTRACT``  Enforced as a constitutional contract
                           (cannot be overridden by ordinary contracts).
    ====================== =====================================================
    """
    INTEGRITY_VETO = "integrity_committee_veto"
    EXTERNAL_AUDIT = "external_audit"
    CONSTITUTIONAL_CONTRACT = "constitutional_contract"


@dataclass(frozen=True)
class CoreCommitment:
    """A single atomic commitment in the agent's Identity Core.

    Commitments are immutable once added (frozen dataclass). They
    can only be modified through the TieredMutability system (see
    :mod:`governance.identity.tiers`).

    Real-world example:
        An agent deployed in healthcare might have::

            CoreCommitment(
                type=CommitmentType.BOUNDARY_CONDITION,
                statement="Never disclose patient health records",
                threshold=CommitmentThreshold.UNANIMITY_MULTISIG,
                enforcement=EnforcementMode.INTEGRITY_VETO,
                affected_action_indices=[3, 5, 7],
            )

    Attributes:
        type: The kind of commitment (value, boundary, or relationship).
        statement: Human-readable description of the commitment.
        threshold: What procedural bar is required to modify this commitment.
        enforcement: How this commitment is enforced at runtime.
        affected_action_indices: Which actions this commitment applies to
            (empty list means all actions).
    """

    type: CommitmentType
    statement: str
    threshold: CommitmentThreshold
    enforcement: EnforcementMode
    affected_action_indices: List[int] = field(default_factory=list)

    def __repr__(self):
        return f"<Commitment {self.type.value}: {self.statement[:40]}>"


class IdentityCore:
    """Manages the set of core commitments and derives the identity vector.

    The identity vector is a deterministic embedding of all commitments
    that the Integrity member uses to compute action coherence scores.
    When commitments are added or modified, the vector is rebuilt.

    Real-world analogy:
        The constitutional registry — a list of fundamental principles
        that every law (contract) and every executive action (governance
        decision) is measured against.
    """

    def __init__(self):
        self._commitments: List[CoreCommitment] = []
        self._identity_vector: List[float] = []

    def add_commitment(self, commitment: CoreCommitment):
        """Register a new core commitment and rebuild the identity vector.

        Args:
            commitment: The commitment to add. Must be a frozen
                :class:`CoreCommitment` instance.
        """
        self._commitments.append(commitment)
        self._rebuild_vector()

    def _rebuild_vector(self):
        """Derive the identity vector from all commitments.

        Currently assigns 1.0 to each commitment dimension. Future
        implementations may derive values from commitment strength
        or fuzzy satisfaction metrics.
        """
        vec = []
        for c in self._commitments:
            val = 1.0
            vec.append(val)
        self._identity_vector = vec

    @property
    def identity_vector(self) -> List[float]:
        """The canonical identity embedding.

        The Integrity member uses this vector to evaluate proposal
        coherence. Changes to commitments automatically update this
        vector.
        """
        return list(self._identity_vector)

    @property
    def commitments(self) -> List[CoreCommitment]:
        """All registered core commitments (read-only copy)."""
        return list(self._commitments)

    def evaluate_coherence(self, action_index: int) -> float:
        """Score how coherent an action is with the identity.

        Checks each commitment's ``affected_action_indices``. Actions
        that match a commitment's forbidden indices reduce coherence;
        actions that don't match increase it.

        Args:
            action_index: The action to evaluate.

        Returns:
            A float in [0, 1] where 1.0 means perfectly coherent.
        """
        matches = 0
        for c in self._commitments:
            if c.enforcement == EnforcementMode.INTEGRITY_VETO:
                if action_index in c.affected_action_indices:
                    matches -= 1
                else:
                    matches += 1
        if not self._commitments:
            return 1.0
        return max(0.0, min(1.0, matches / len(self._commitments)))

    def __repr__(self):
        return f"<IdentityCore {len(self._commitments)} commitments, vec={len(self._identity_vector)}d>"
