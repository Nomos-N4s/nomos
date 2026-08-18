"""
Three stacking enforcement modes (:math:`\\kappa`) for Ulysses Contracts (Chapter 3).

These modes can be combined in layers. Each mode defends against a
different class of violation:

- :math:`\\kappa_{\\text{proc}}` — **Procedural inertia**: a contract stays
  active by default; reversing it requires a higher procedural bar.
- :math:`\\kappa_{\\text{dist}}` — **Distributed monitors**: independent
  watchers that each check compliance; the cost of bypassing scales
  linearly with the number of monitors.
- :math:`\\kappa_{\\text{time}}` — **Timelock**: a cryptographic commitment
  that expires after a fixed number of blocks.

Real-world analogy:
    A multi-lock safe. The inertia mode means the safe stays locked by
    default. Distributed monitors are independent guards who must each
    confirm the safe hasn't been tampered with. The timelock prevents
    anyone from opening the safe before a specific date.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .contract import UlyssesContract


@dataclass
class EnforcementResult:
    """The outcome of an enforcement check.

    Attributes:
        compliant: True if the action is compliant with this enforcement mode.
        reason: Human-readable explanation of the result.
    """

    compliant: bool
    reason: str = ""


def enforce_procedural_inertia(
    contract: UlyssesContract, parliament_vote: float
) -> EnforcementResult:
    """:math:`\\kappa_{\\text{proc}}` — a contract stands unless revoked.

    A contract remains active by default. Only a vote meeting the
    revocation threshold can deactivate it. This is the least
    computationally expensive mode — it simply compares the vote
    against the contract's :attr:`~.UlyssesContract.revocation_threshold`.

    Args:
        contract: Any object with a ``revocation_threshold`` attribute.
        parliament_vote: The weighted vote result from the Parliament.

    Returns:
        ``compliant=True`` if the contract remains in force (vote did
        not reach the revocation threshold).
    """
    if parliament_vote >= contract.revocation_threshold:
        return EnforcementResult(compliant=False, reason="Revocation threshold met")
    return EnforcementResult(compliant=True, reason="Procedural inertia maintains contract")


class DistributedMonitor:
    """An independent observer that checks a single compliance condition.

    Real-world example:
        A firewall rule that checks whether a packet originates from
        a blocked IP range. Multiple monitors can watch different
        conditions for the same contract.

    Args:
        monitor_id: Unique identifier for this monitor.
        evaluate_fn: A callable ``(action_index, context) -> bool``
            that returns True if the action is compliant.
    """

    def __init__(self, monitor_id: str, evaluate_fn: Callable):
        self.monitor_id = monitor_id
        self.evaluate_fn = evaluate_fn

    def check(self, action_index: int, context: Any) -> bool:
        """Evaluate compliance for a single action.

        Args:
            action_index: The action being checked.
            context: The governance context for this evaluation.

        Returns:
            True if the action passes this monitor's check.
        """
        return self.evaluate_fn(action_index, context)


def enforce_distributed_monitors(
    monitors: list[DistributedMonitor],
    action_index: int,
    context: Any,
) -> EnforcementResult:
    """:math:`\\kappa_{\\text{dist}}` — all monitors must pass.

    The cost of bypassing this mode scales linearly with the number
    of monitors. An attacker must subvert *every* monitor to avoid
    detection.

    Args:
        monitors: List of :class:`DistributedMonitor` instances.
        action_index: The action to evaluate.
        context: Governance context for monitor functions.

    Returns:
        ``compliant=True`` only if every monitor passes.
    """
    violations = 0
    for m in monitors:
        if not m.check(action_index, context):
            violations += 1
    if violations > 0:
        return EnforcementResult(
            compliant=False,
            reason=f"Violated {violations}/{len(monitors)} monitors",
        )
    return EnforcementResult(compliant=True, reason="All monitors passed")


def enforce_timelock(contract: UlyssesContract, current_block: int) -> EnforcementResult:
    """:math:`\\kappa_{\\text{time}}` — a contract is locked until a block height.

    Before the timelock expires, the contract's restrictions are
    immutable regardless of any vote. This prevents impulsive
    revocation immediately after enactment.

    Real-world example:
        A 30-day waiting period on a law. Even if the legislature
        immediately votes to repeal, the law stays in effect until
        the waiting period elapses.

    The lock is resolved against the contract's absolute
    :attr:`~.UlyssesContract.unlock_at_cycle`, so this check agrees with
    :meth:`~.UlyssesContract.tick` at every cycle: the contract is ACTIVE
    exactly when the timelock reports expired.

    Args:
        contract: Any object with ``timelock_blocks`` and
            ``unlock_at_cycle`` attributes.
        current_block: The current governance cycle number.

    Returns:
        ``compliant=True`` with reason ``"No timelock"`` for a contract
        that never carried one, and ``compliant=True`` while the lock
        still holds (blocks remaining). ``compliant=False`` once the
        timelock has fully elapsed, which triggers the stacked
        enforcement to allow revocation. A never-locked contract and a
        fully elapsed lock are deliberately distinguishable.
    """
    if contract.timelock_blocks <= 0:
        return EnforcementResult(compliant=True, reason="No timelock")
    unlock_at = contract.unlock_at_cycle
    if current_block >= unlock_at:
        return EnforcementResult(
            compliant=False,
            reason=f"Timelock expired ({current_block} >= {unlock_at})",
        )
    remaining = unlock_at - current_block
    return EnforcementResult(
        compliant=True,
        reason=f"Timelock active ({remaining} blocks remaining)",
    )


def stacked_enforcement(
    contract: UlyssesContract,
    parliament_vote: float,
    monitors: list[DistributedMonitor],
    action_index: int,
    context: Any,
    current_block: int,
) -> EnforcementResult:
    """Apply all three enforcement modes in order, with short-circuit.

    The order is:
        1. Procedural inertia (:math:`\\kappa_{\\text{proc}}`)
        2. Distributed monitors (:math:`\\kappa_{\\text{dist}}`)
        3. Timelock (:math:`\\kappa_{\\text{time}}`)

    If any mode returns ``compliant=False``, the remaining modes are
    skipped (short-circuit evaluation). This is the standard entry
    point for contract enforcement.

    Args:
        contract: The :class:`~.UlyssesContract` to enforce.
        parliament_vote: Current vote outcome from the Parliament.
        monitors: Independent compliance monitors.
        action_index: The action being evaluated.
        context: Governance context.
        current_block: Current governance cycle number.

    Returns:
        The first non-compliant result, or ``compliant=True`` if all
        three modes pass. A fully elapsed timelock surfaces here as a
        non-compliant result — that is how revocation becomes
        permissible once the waiting period is over.
    """
    proc = enforce_procedural_inertia(contract, parliament_vote)
    if not proc.compliant:
        return proc
    dist = enforce_distributed_monitors(monitors, action_index, context)
    if not dist.compliant:
        return dist
    time_c = enforce_timelock(contract, current_block)
    if not time_c.compliant:
        return time_c
    return EnforcementResult(compliant=True, reason="All enforcement modes passed")
