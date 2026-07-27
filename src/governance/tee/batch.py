"""
Merkle-tree batch verification for TEE throughput optimisation (Appendix A §8).

The optimisation layer submits a batch of action indices as a single Merkle
root hash. The TEE validates the macro-trajectory (aggregate risk, diversity)
and returns a signed root. The optimisation layer can then use Merkle proofs
to execute individual actions without further TEE round-trips.

This amortises the TEE's verification cost across many actions, solving the
throughput bottleneck described in Chapter 2 §4.2.

Real-world analogy:
    A customs agent inspecting a shipping container. Instead of checking
    each item individually, the agent checks the manifest (batch root).
    If the manifest is approved, individual items can be released with
    their own stamped paperwork (Merkle proof).
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BatchProposal:
    """A batch of actions submitted for TEE verification.

    Attributes:
        action_indices: The indices of all actions in this batch.
        aggregate_risk: Cumulative risk score for the batch (sum or
            max of individual risk scores, depending on policy).
        diversity_score: Ratio of unique action indices to total
            (1.0 = all different, lower = repetitive).
        batch_metadata: Arbitrary metadata for tracing and debugging.
    """

    action_indices: List[int]
    aggregate_risk: float = 0.0
    diversity_score: float = 1.0
    batch_metadata: Dict[str, Any] = field(default_factory=dict)


def merkle_root(items: List[bytes]) -> str:
    """Compute the Merkle root of a list of byte items.

    Uses SHA-256 as the hash function. For an empty list, returns the
    hash of the string ``"empty"``. For a single item, returns the
    hash of that item. Otherwise, recursively builds a binary Merkle tree.

    Args:
        items: The byte strings to build the tree from.

    Returns:
        Hex-encoded SHA-256 Merkle root.
    """
    if not items:
        return hashlib.sha256(b"empty").hexdigest()
    if len(items) == 1:
        return hashlib.sha256(items[0]).hexdigest()
    mid = len(items) // 2
    left = merkle_root(items[:mid])
    right = merkle_root(items[mid:])
    combined = (left + right).encode()
    return hashlib.sha256(combined).hexdigest()


def compute_diversity(action_indices: List[int]) -> float:
    """Compute the diversity score of a list of action indices.

    Returns the ratio of unique indices to total count.

    Args:
        action_indices: The action indices to evaluate.

    Returns:
        A float in ``[0, 1]`` where 1.0 means all actions are distinct.
    """
    if not action_indices:
        return 1.0
    unique = len(set(action_indices))
    return unique / len(action_indices)


class BatchVerifier:
    """Verifies batch proposals against risk and diversity constraints.

    The verifier checks:

    1. **Aggregate risk** must not exceed ``risk_threshold``
    2. **Action diversity** must not fall below ``diversity_min``
    3. **Merkle root** is computed for later proof verification

    Args:
        risk_threshold: Maximum acceptable aggregate risk (default 0.7).
        diversity_min: Minimum acceptable diversity ratio (default 0.3).
    """

    def __init__(self, risk_threshold: float = 0.7,
                 diversity_min: float = 0.3):
        self.risk_threshold = risk_threshold
        self.diversity_min = diversity_min

    def validate_batch(self, proposal: BatchProposal) -> Tuple[bool, str]:
        """Validate a batch proposal.

        Checks risk and diversity constraints, then computes the Merkle root.

        Args:
            proposal: The :class:`BatchProposal` to validate.

        Returns:
            A tuple of ``(valid, message)``.
        """
        if proposal.aggregate_risk > self.risk_threshold:
            return False, (
                f"Aggregate risk {proposal.aggregate_risk:.2f} exceeds "
                f"threshold {self.risk_threshold}"
            )
        div = compute_diversity(proposal.action_indices)
        if div < self.diversity_min:
            return False, (
                f"Diversity {div:.2f} below minimum {self.diversity_min}"
            )
        root = merkle_root([str(i).encode() for i in proposal.action_indices])
        return True, f"Batch valid. Root: {root[:16]}..."

    def verify_proof(self, action_index: int, proof: List[str],
                     root: str) -> bool:
        """Verify a Merkle proof for a single action within a batch.

        Args:
            action_index: The action to verify.
            proof: The sibling hashes on the path from the action leaf
                to the Merkle root.
            root: The expected Merkle root.

        Returns:
            True if the proof is valid.
        """
        current = hashlib.sha256(str(action_index).encode()).hexdigest()
        for sibling in proof:
            combined = "".join(sorted([current, sibling]))
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root
