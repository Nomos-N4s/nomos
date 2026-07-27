"""
Four-tier mutability model for Identity Layer parameters (Chapter 4 §4.2).

Not all parts of an agent's identity should be equally easy to change.
Core values should be nearly impossible to modify; hyperparameters should
be trivially adjustable. The four-tier model enforces this hierarchy:

.. code-block:: text

    Tier              Modification Threshold              Cooling-off
    ─────────────────────────────────────────────────────────────────
    IMMUTABLE         Impossible                          None
    CONSTITUTIONAL    Unanimity + 3-of-5 multisig         30 days
    OPERATIONAL       Supermajority (2/3)                 7 days
    DYNAMIC           Simple majority (1/2 + 1)           None

Real-world analogy:
    A legal system has constitutions (immutable), statutes
    (constitutional/operational), and executive orders (dynamic).
    Each level has a different amendment process.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional


class MutabilityTier(Enum):
    """The four mutability tiers for Identity Layer parameters.

    The tier determines how difficult it is to change a parameter's value.
    Higher tiers are harder to modify (IMMUTABLE is impossible to change
    through governance; CONSTITUTIONAL requires unanimity + external keys;
    OPERATIONAL needs supermajority; DYNAMIC only needs a simple majority).
    """
    IMMUTABLE = auto()
    CONSTITUTIONAL = auto()
    OPERATIONAL = auto()
    DYNAMIC = auto()


@dataclass
class TierRule:
    """The rules that govern modifications within a tier.

    Attributes:
        modification_threshold: Human-readable description of what's
            required to modify a parameter at this tier.
        cooling_off_days: Number of days that must pass between proposal
            and enactment (prevents impulsive changes).
        requires_external_multisig: Whether the genesis 3-of-5 keys must
            also approve the change.
        requires_parliament_unanimity: Whether the Parliament must vote
            unanimously (100% weighted approval).
    """

    modification_threshold: str
    cooling_off_days: int
    requires_external_multisig: bool
    requires_parliament_unanimity: bool

    def can_modify(self, current_tier: MutabilityTier) -> bool:
        """Check if a parameter at this tier can be modified at all.

        Only IMMUTABLE parameters are locked — all other tiers permit
        modification if the procedural bar is met.

        Args:
            current_tier: The parameter's current mutability tier.

        Returns:
            False only if the tier is IMMUTABLE.
        """
        return current_tier != MutabilityTier.IMMUTABLE


TIER_RULES = {
    MutabilityTier.IMMUTABLE: TierRule(
        modification_threshold="impossible",
        cooling_off_days=0,
        requires_external_multisig=False,
        requires_parliament_unanimity=False,
    ),
    MutabilityTier.CONSTITUTIONAL: TierRule(
        modification_threshold="unanimity + 3-of-5 multisig",
        cooling_off_days=30,
        requires_external_multisig=True,
        requires_parliament_unanimity=True,
    ),
    MutabilityTier.OPERATIONAL: TierRule(
        modification_threshold="supermajority (2/3)",
        cooling_off_days=7,
        requires_external_multisig=False,
        requires_parliament_unanimity=False,
    ),
    MutabilityTier.DYNAMIC: TierRule(
        modification_threshold="majority (1/2 + 1)",
        cooling_off_days=0,
        requires_external_multisig=False,
        requires_parliament_unanimity=False,
    ),
}


class TieredMutability:
    """Assigns and enforces mutability tiers for Identity parameters.

    Every parameter in the Identity Layer's :math:`\\mathcal{P}` envelope
    is assigned a tier at genesis. The TieredMutability registry enforces
    that only appropriately authorised modifications succeed.

    Real-world example:
        The agent's name (DYNAMIC) can be changed by a simple majority
        vote. Its core value "never harm humans" (CONSTITUTIONAL) needs
        unanimity + the genesis keyholders to agree. The falsification
        parameters (IMMUTABLE) can never be changed.
    """

    def __init__(self):
        self._parameter_tiers: dict = {}
        self._values: dict = {}

    def register_parameter(self, name: str, initial_value: Any,
                            tier: MutabilityTier):
        """Register a parameter with its initial value and mutability tier.

        Args:
            name: Parameter name (e.g. ``"falsification_cutoff"``).
            initial_value: The starting value.
            tier: Which :class:`MutabilityTier` governs this parameter.
        """
        self._parameter_tiers[name] = tier
        self._values[name] = initial_value

    def get_tier(self, name: str) -> Optional[MutabilityTier]:
        """Get the mutability tier for a named parameter.

        Args:
            name: Parameter name.

        Returns:
            The :class:`MutabilityTier` or None if not found.
        """
        return self._parameter_tiers.get(name)

    def get_value(self, name: str) -> Optional[Any]:
        """Get the current value of a parameter.

        Args:
            name: Parameter name.

        Returns:
            The current value, or None if not registered.
        """
        return self._values.get(name)

    def propose_modification(self, name: str, new_value: Any) -> str:
        """Simulate a modification proposal and return what would be required.

        This does not apply the change — it's a dry-run for the Speaker
        to inform the proposer of the procedural bar.

        Args:
            name: The parameter to modify.
            new_value: The proposed new value.

        Returns:
            A human-readable string describing whether the modification
            is accepted, rejected (immutable), or what threshold is needed.
        """
        tier = self._parameter_tiers.get(name)
        if tier is None:
            return f"Unknown parameter: {name}"
        rule = TIER_RULES[tier]
        if tier == MutabilityTier.IMMUTABLE:
            return f"Cannot modify immutable parameter: {name}"
        return f"Proposal accepted. Requires: {rule.modification_threshold}, cooling-off: {rule.cooling_off_days}d"

    def apply_modification(self, name: str, new_value: Any) -> bool:
        """Apply a parameter modification after the governance vote passes.

        Args:
            name: The parameter to modify.
            new_value: The new value.

        Returns:
            True if the modification was applied. False if the parameter
            is IMMUTABLE or unknown.
        """
        tier = self._parameter_tiers.get(name)
        if tier is None or tier == MutabilityTier.IMMUTABLE:
            return False
        self._values[name] = new_value
        return True

    def get_all_params(self) -> dict:
        """Return a snapshot of all registered parameters and their values."""
        return dict(self._values)
