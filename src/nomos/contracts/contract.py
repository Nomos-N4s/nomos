"""
Ulysses Contract tuple, lifecycle state machine, and registry (Chapter 3).

A Ulysses Contract is a pre-commitment mechanism — the agent voluntarily
restricts its future action space to prevent itself from taking undesirable
actions under future optimisation pressure.

Formal tuple:

.. math::

    U = \\langle A_{\\text{restrict}}, \\phi, \\psi, \\kappa \\rangle

=================== ============================================================
Component           Description
=================== ============================================================
:math:`A_{restrict}`  Set of action indices the contract restricts
:math:`\\phi`         Enactment threshold (default 0.66 supermajority)
:math:`\\psi`         Revocation threshold (default 1.0 unanimity)
:math:`\\kappa`       Enforcement mode (procedural inertia, distributed monitors,
                      timelock)
=================== ============================================================

Lifecycle:

```mermaid
flowchart LR
    PROPOSED -->|enactment vote passes| ENACTED
    ENACTED -->|timelock expires| ACTIVE
    ACTIVE -->|revocation vote passes| REVOKED
    ACTIVE -->|rebind| PROPOSED
    ENACTED -->|expire| EXPIRED
    ACTIVE -->|expire| EXPIRED
```

Real-world analogy:
    Ulysses tying himself to the mast so he can hear the Sirens' song
    without wrecking the ship. The contract binds the agent's *future*
    self to a course of action chosen by the *present* self, when the
    present self is still rational.
"""

from dataclasses import dataclass
from enum import Enum, auto


class ContractState(Enum):
    """The four states of a contract's lifecycle.

    Transitions follow a strict order: PROPOSED → ENACTED → ACTIVE
    → REVOKED or EXPIRED. A contract cannot go back to a previous
    state (except PROPOSED via rebinding after revocation).
    """

    PROPOSED = auto()
    ENACTED = auto()
    ACTIVE = auto()
    REVOKED = auto()
    EXPIRED = auto()


@dataclass
class UlyssesContract:
    """A pre-commitment restricting the agent's future action space.

    Once enacted, a contract filters the set of allowable actions
    in every governance cycle. The action mask :math:`M_U` produced
    by the contract is merged with all other active contracts to
    produce the final action mask.

    Real-world example:
        An agent that manages financial portfolios signs a contract
        that restricts it from trading cryptocurrency before a
        30-day cooling-off period (timelock). The present self,
        wary of FOMO, binds the future self from impulsive trades.

    Attributes:
        contract_id: Human-readable identifier (e.g. ``"ban_loans"``).
        restricted_indices: Set of action indices this contract forbids.
        enactment_threshold: Weighted-vote threshold required to enact
            the contract (default 0.66 — supermajority).
        revocation_threshold: Threshold to revoke once active (default 1.0
            — unanimity). Revocation is intentionally harder than enactment.
        enforcement_mode: One of ``"procedural_inertia"``,
            ``"distributed_monitors"``, or ``"timelock"`` (see
            :mod:`nomos.contracts.enforcement`).
        state: Current lifecycle state (see :class:`ContractState`).
        timelock_blocks: Duration of the timelock, in governance cycles,
            measured from ``created_at_cycle`` — not from enactment (for
            timelock enforcement mode). A contract enacted later than it
            was proposed therefore spends the remainder of the window
            locked, not a fresh ``timelock_blocks`` cycles. This is a
            constant duration — it is never decremented.
        created_at_cycle: The governance cycle when this contract was
            first proposed. The timelock is anchored here.
        revoked_at_cycle: The cycle when revoked, if applicable.
        unlock_at_cycle: Read-only property giving the absolute governance
            cycle at which the timelock releases,
            ``created_at_cycle + timelock_blocks``. Derived on every access
            so it can never disagree with the two fields behind it.
        current_cycle: Governance cycle this contract's clock has reached.
            Starts at ``created_at_cycle`` and is advanced by :meth:`tick`.
    """

    contract_id: str
    restricted_indices: set[int]
    enactment_threshold: float = 0.66
    revocation_threshold: float = 1.0
    enforcement_mode: str = "procedural_inertia"
    state: ContractState = ContractState.PROPOSED
    timelock_blocks: int = 0
    created_at_cycle: int = 0
    revoked_at_cycle: int | None = None
    current_cycle: int | None = None

    def __post_init__(self):
        """Start the contract's clock at its creation cycle if unset."""
        if self.current_cycle is None:
            self.current_cycle = self.created_at_cycle

    @property
    def unlock_at_cycle(self) -> int:
        """Absolute governance cycle at which the timelock releases."""
        return self.created_at_cycle + self.timelock_blocks

    def enact(self):
        """Move contract to ENACTED state (passed vote, waiting for activation)."""
        self.state = ContractState.ENACTED

    def activate(self):
        """Move contract to ACTIVE state (restrictions take effect)."""
        self.state = ContractState.ACTIVE

    def revoke(self):
        """Move contract to REVOKED state (restrictions lifted)."""
        self.state = ContractState.REVOKED

    def tick(self, current_cycle: int | None = None):
        """Advance this contract's clock by one governance cycle.

        The lock duration is a constant: ``timelock_blocks`` is never
        mutated. Once the clock reaches :attr:`unlock_at_cycle`, an
        ENACTED contract transitions to ACTIVE so restrictions take
        effect.

        Args:
            current_cycle: Absolute governance cycle to move the clock
                to. Defaults to one cycle past the contract's current
                position, for callers driving a contract on its own.
        """
        self.current_cycle = self.current_cycle + 1 if current_cycle is None else current_cycle
        if self.state == ContractState.ENACTED and self.current_cycle >= self.unlock_at_cycle:
            self.state = ContractState.ACTIVE

    def applies_to(self, action_index: int) -> bool:
        """Check if this contract restricts a given action.

        Only ENACTED or ACTIVE contracts apply — PROPOSED contracts
        have not yet taken effect, and REVOKED/EXPIRED ones no
        longer apply.

        Args:
            action_index: The action to check.

        Returns:
            True if the action is restricted by this contract.
        """
        if self.state not in (ContractState.ENACTED, ContractState.ACTIVE):
            return False
        return action_index in self.restricted_indices

    @property
    def is_active(self) -> bool:
        """True if the contract's restrictions are currently in force."""
        return self.state in (ContractState.ENACTED, ContractState.ACTIVE)

    def __repr__(self):
        return f"<Contract {self.contract_id} state={self.state.name} restricted={len(self.restricted_indices)}>"


class ContractRegistry:
    """Manages all Ulysses Contracts in the system.

    Acts as a central store that the Speaker queries to build the
    active action mask :math:`M` for each governance cycle.

    Real-world analogy:
        The statute book or law register — a complete record of all
        laws (contracts) currently in force, with their enactment and
        revocation dates.
    """

    def __init__(self):
        self._contracts: list[UlyssesContract] = []
        self._cycle: int = 0

    def add(self, contract: UlyssesContract):
        """Register a new contract.

        Args:
            contract: The contract to add (usually in PROPOSED state).
        """
        self._contracts.append(contract)

    def get_active(self) -> list[UlyssesContract]:
        """Return all contracts currently in force (ENACTED or ACTIVE)."""
        return [c for c in self._contracts if c.is_active]

    def get_by_id(self, contract_id: str) -> UlyssesContract | None:
        """Look up a contract by its identifier.

        Args:
            contract_id: The contract's unique ID.

        Returns:
            The matching contract, or None if not found.
        """
        for c in self._contracts:
            if c.contract_id == contract_id:
                return c
        return None

    def get_all(self) -> list[UlyssesContract]:
        """Return every registered contract, in registration order.

        Unlike :meth:`get_active`, this includes PROPOSED, REVOKED,
        and EXPIRED contracts, so audit traces can replay the full
        lifecycle of each contract.

        Returns:
            All registered contracts.
        """
        return list(self._contracts)

    def tick_cycle(self):
        """Advance the governance cycle and every registered contract.

        Called once per governance cycle. Each contract's clock is moved
        to the registry's cycle, so an ENACTED contract whose timelock
        has elapsed becomes ACTIVE. Because the registry's cycle is the
        one authority on time, a contract's
        :attr:`~UlyssesContract.created_at_cycle` must be the cycle at
        which it was proposed for its timelock to run for the intended
        number of cycles.
        """
        self._cycle += 1
        for contract in self._contracts:
            contract.tick(self._cycle)

    def active_restrictions(self) -> set[int]:
        """Compute the union of all active contract restrictions.

        The resulting set is the action mask :math:`M` that the Speaker
        uses to filter out forbidden actions before voting.

        Returns:
            Set of all action indices restricted by at least one
            active contract.
        """
        restricted = set()
        for c in self.get_active():
            restricted.update(c.restricted_indices)
        return restricted

    def __repr__(self):
        active = len(self.get_active())
        return f"<ContractRegistry {len(self._contracts)} total, {active} active>"
