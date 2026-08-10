"""
Parameter envelope :math:`\\mathcal{P}` of the Identity Layer (Chapter 4 §4.4).

Defines which Speaker parameters the Identity Layer can constrain, and
their valid bounds. The envelope is the box the agent must stay within —
it cannot set parameters outside these bounds even if the Parliament votes
unanimously.

Real-world analogy:
    A constitution that says "the legislature may set the tax rate between
    10% and 30%." The legislature has discretion *within* the bounds, but
    can never go outside them, even with a unanimous vote.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class BoundedParameter:
    """A single parameter with a default value and valid range.

    Attributes:
        name: Parameter name.
        default: Default value, used if ``current`` is not explicitly set.
        bounds: A ``(min, max)`` tuple. Either bound may be ``None``
            (unbounded on that side).
        current: The current runtime value. Initialises to ``default``
            if not provided.
    """

    name: str
    default: Any
    bounds: tuple[Any, Any]
    current: Any = None

    def __post_init__(self):
        if self.current is None:
            self.current = self.default

    def set(self, value: Any) -> bool:
        """Set a new value, subject to bounds.

        Args:
            value: The desired value.

        Returns:
            True if the value was within bounds and set. False otherwise.
        """
        low, high = self.bounds
        if low is not None and value < low:
            return False
        if high is not None and value > high:
            return False
        self.current = value
        return True


class ParameterEnvelope:
    """Registry of all bounded parameters in the Identity Layer.

    Each registered parameter is constrained by its bounds. Any attempt
    to set a value outside the bounds fails silently (returns False).

    Real-world example:
        The ``quorum_threshold`` parameter is bounded to [0.3, 0.7].
        The Parliament can adjust the quorum within that range, but can
        never set it below 0.3 (which would make decisions too easy) nor
        above 0.7 (which would cause gridlock).
    """

    def __init__(self):
        self._params: dict[str, BoundedParameter] = {}

    def register(self, name: str, default: Any, bounds: tuple[Any, Any]):
        """Add a parameter to the envelope.

        Args:
            name: Unique identifier for the parameter.
            default: Starting value.
            bounds: ``(min, max)`` range.
        """
        self._params[name] = BoundedParameter(
            name=name,
            default=default,
            bounds=bounds,
        )

    def get(self, name: str) -> Any | None:
        """Get a parameter's current value.

        Args:
            name: Parameter name.

        Returns:
            Current value, or None if not found.
        """
        p = self._params.get(name)
        return p.current if p else None

    def set(self, name: str, value: Any) -> bool:
        """Set a parameter's value (checks bounds internally).

        Args:
            name: Parameter name.
            value: Desired value.

        Returns:
            True if set successfully, False if out of bounds or unknown.
        """
        p = self._params.get(name)
        if p is None:
            return False
        return p.set(value)

    def reset_to_defaults(self):
        """Reset all parameters to their original defaults."""
        for p in self._params.values():
            p.current = p.default

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of all current parameter values.

        Used by the Identity Layer's coherence checks and for
        serialisation in the :class:`~.GenesisManifest`.
        """
        return {n: p.current for n, p in self._params.items()}


DEFAULT_PARAMETER_ENVELOPE = ParameterEnvelope()
DEFAULT_PARAMETER_ENVELOPE.register("quorum_threshold", 0.5, (0.3, 0.7))
DEFAULT_PARAMETER_ENVELOPE.register("max_deliberation_rounds", 3, (1, 10))
DEFAULT_PARAMETER_ENVELOPE.register("member_min_budget", 1, (1, 20))
DEFAULT_PARAMETER_ENVELOPE.register("deadlock_threshold_cycles", 100, (10, 1000))
