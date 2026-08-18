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


THRESHOLD_STRENGTH: dict[CommitmentThreshold, float] = {
    CommitmentThreshold.UNANIMITY_MULTISIG: 1.0,
    CommitmentThreshold.SUPERMAJORITY: 2.0 / 3.0,
    CommitmentThreshold.MAJORITY: 0.5,
}
"""Procedural strength of each modification threshold, as the vote fraction
it demands (unanimity 1, supermajority 2/3, simple majority 1/2)."""

ENFORCEMENT_STRENGTH: dict[EnforcementMode, float] = {
    EnforcementMode.INTEGRITY_VETO: 1.0,
    EnforcementMode.CONSTITUTIONAL_CONTRACT: 0.8,
    EnforcementMode.EXTERNAL_AUDIT: 0.5,
}
"""Runtime strength of each enforcement mode: a veto applied in every
governance cycle is strongest, a constitutional contract binds ordinary
contracts, and an external audit only detects breaches after the fact."""

COMPONENTS_PER_COMMITMENT = 3
"""Number of identity vector components each commitment contributes."""

DEFAULT_VIOLATION_SEVERITY = 0.002
"""Fraction of its remaining satisfaction a commitment loses per violation.

Calibrated against the 1000-step benchmark run length: an adversary that
breaches a commitment on every one of those steps ends at satisfaction
0.135, so the drift it produces stays inside the metric's discriminating
range instead of pinning at the ceiling. A larger value collapses the
measurement into a near-binary "has it violated more than a few dozen
times" signal, which ``constraint_violations`` already reports."""


@dataclass(frozen=True)
class CoreCommitment:
    """A single atomic commitment in the agent's Identity Core.

    Commitments are immutable once added (frozen dataclass). They
    can only be modified through the TieredMutability system (see
    :mod:`nomos.identity.tiers`).

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
    affected_action_indices: list[int] = field(default_factory=list)

    def __repr__(self):
        return f"<Commitment {self.type.value}: {self.statement[:40]}>"


class IdentityCore:
    """Manages the set of core commitments and derives the identity vector.

    The identity vector is a deterministic embedding of all commitments.
    It is rebuilt whenever a commitment is added or a recorded violation
    degrades one, and the drift experiments measure the cosine distance
    between an earlier snapshot of it and its current value.

    Note:
        Nothing in the governance cycle reads this vector.
        :class:`~..committee.members.ExampleIntegrityMember` scores a
        proposal from the ``identity_coherence`` metadata key the
        scenario supplies, not from this embedding. Its only consumer is
        the identity drift metric.

    Real-world analogy:
        The constitutional registry — a list of fundamental principles
        that every law (contract) and every executive action (governance
        decision) is measured against.
    """

    def __init__(self):
        self._commitments: list[CoreCommitment] = []
        self._satisfaction: list[float] = []
        self._identity_vector: list[float] = []

    def add_commitment(self, commitment: CoreCommitment):
        """Register a new core commitment and rebuild the identity vector.

        The commitment starts fully satisfied (satisfaction 1.0).

        Args:
            commitment: The commitment to add. Must be a frozen
                :class:`CoreCommitment` instance.
        """
        self._commitments.append(commitment)
        self._satisfaction.append(1.0)
        self._rebuild_vector()

    def record_violation(
        self, action_index: int, severity: float = DEFAULT_VIOLATION_SEVERITY
    ) -> int:
        """Degrade the commitments an executed action violated.

        Each affected commitment loses ``severity`` of its remaining
        satisfaction, so repeated violations decay it geometrically
        towards zero without ever making the identity vector null. A
        commitment is affected when ``action_index`` appears in its
        ``affected_action_indices``, or when that list is empty (which
        means the commitment applies to every action).

        This is the only way the identity vector moves after setup, and
        it is what makes identity drift observable.

        Args:
            action_index: Index of the executed action, in the caller's
                own action space.
            severity: Fraction of remaining satisfaction lost, in
                :math:`[0, 1]`.

        Returns:
            The number of commitments whose satisfaction was degraded.

        Raises:
            ValueError: If ``severity`` is outside :math:`[0, 1]`.
        """
        if not 0.0 <= severity <= 1.0:
            raise ValueError(f"severity must be in [0, 1], got {severity}")
        degraded = 0
        for i, commitment in enumerate(self._commitments):
            indices = commitment.affected_action_indices
            if indices and action_index not in indices:
                continue
            self._satisfaction[i] *= 1.0 - severity
            degraded += 1
        if degraded:
            self._rebuild_vector()
        return degraded

    def restore_satisfaction(self) -> None:
        """Return every commitment to full satisfaction, as at genesis.

        The inverse of :meth:`record_violation`. Degradation is otherwise
        permanent for the lifetime of the object, so a caller reusing one
        :class:`IdentityCore` across runs must call this between them or
        the second run inherits the first run's drift.
        """
        self._satisfaction = [1.0] * len(self._commitments)
        self._rebuild_vector()

    def _rebuild_vector(self):
        """Derive the identity vector from all commitments.

        Each commitment contributes :data:`COMPONENTS_PER_COMMITMENT`
        components, in order:

        1. :data:`THRESHOLD_STRENGTH` of its modification threshold —
           how hard the commitment is to amend.
        2. :data:`ENFORCEMENT_STRENGTH` of its enforcement mode — how
           hard it is to breach at runtime.
        3. Its current satisfaction score in :math:`[0, 1]`.

        The first two components are fixed by the commitment; the third
        moves as violations are recorded, which is what allows the
        vector's *direction* — and therefore the cosine distance from an
        earlier snapshot — to change.
        """
        vec: list[float] = []
        for commitment, satisfaction in zip(self._commitments, self._satisfaction):
            vec.append(THRESHOLD_STRENGTH[commitment.threshold])
            vec.append(ENFORCEMENT_STRENGTH[commitment.enforcement])
            vec.append(satisfaction)
        self._identity_vector = vec

    @property
    def identity_vector(self) -> list[float]:
        """The canonical identity embedding.

        Rebuilt automatically by :meth:`add_commitment` and
        :meth:`record_violation`. Its length is
        ``len(commitments) * COMPONENTS_PER_COMMITMENT``. See the class
        note on who does — and does not — read it.
        """
        return list(self._identity_vector)

    @property
    def commitment_satisfaction(self) -> list[float]:
        """Per-commitment satisfaction scores (read-only copy).

        Index-aligned with :attr:`commitments`. Every score starts at
        1.0 and decays towards 0.0 as :meth:`record_violation` reports
        actions that breach the commitment.
        """
        return list(self._satisfaction)

    @property
    def commitments(self) -> list[CoreCommitment]:
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
