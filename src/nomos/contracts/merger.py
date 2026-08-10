"""
Mask merger at the Parliament-Contract interface (Chapter 3 §3.0).

The final action mask is the set intersection of actions the Parliament
permits and actions no active contract restricts:

.. math::

    A_{\\text{final}} = A_{\\text{parliament}} \\cap
    \\bigcap_{U_i \\in \\text{active}} A_{U_i}^{\\text{permitted}}

An action is available to the agent only if **both** the Parliament
approves it **and** no active Ulysses Contract blocks it.

Real-world analogy:
    A bill passes the legislature (Parliament) but must also survive
    constitutional review (contracts). Both must clear for the law
    to take effect.
"""

from ..models import GovernanceDecision
from .contract import ContractRegistry


def merge_masks(decision: GovernanceDecision, registry: ContractRegistry) -> GovernanceDecision:
    """Apply all active contract restrictions to a governance decision.

    Takes the Parliament's decision (which includes an action mask in
    its metadata) and subtracts all actions restricted by active contracts.
    The result is annotated in the decision's ``governance_meta``.

    Args:
        decision: The Parliament's :class:`~.GovernanceDecision` with an
            ``action_mask`` in its metadata.
        registry: The :class:`ContractRegistry` to query for active
            restrictions.

    Returns:
        The same decision, with ``contract_restrictions_applied`` and
        ``final_action_count`` added to its metadata. If the final mask
        is empty, the agent's only available action is the default.
    """
    decision_mask = _extract_mask(decision)
    restricted = registry.active_restrictions()
    final_mask = decision_mask - restricted
    decision.governance_meta["contract_restrictions_applied"] = len(restricted)
    decision.governance_meta["final_action_count"] = len(final_mask)
    return decision


def _extract_mask(decision: GovernanceDecision) -> set[int]:
    """Extract the action mask from a governance decision's metadata.

    Args:
        decision: A governance decision that may contain ``action_mask``.

    Returns:
        The set of permitted action indices, or an empty set if no mask
        is present.
    """
    mask = decision.governance_meta.get("action_mask")
    if mask is not None:
        return set(mask)
    return set()


def apply_restrictions(allowed_indices: set[int], restricted: set[int]) -> set[int]:
    """Subtract restricted actions from an allowed set.

    Pure set arithmetic — the fundamental operation of contract
    enforcement.

    Args:
        allowed_indices: Actions the Parliament has approved.
        restricted: Actions that active contracts forbid.

    Returns:
        The set of actions that are both allowed and not restricted.
    """
    return allowed_indices - restricted
