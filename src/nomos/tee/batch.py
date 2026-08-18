"""
Merkle-tree batch verification for TEE throughput optimisation (Appendix A §11).

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
from typing import Any

# A sibling path from leaf to root: (sibling_digest, sibling_is_left).
MerkleProof = list[tuple[str, bool]]


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

    action_indices: list[int]
    aggregate_risk: float = 0.0
    diversity_score: float = 1.0
    batch_metadata: dict[str, Any] = field(default_factory=dict)


# Domain-separation tags. Without them a leaf and an internal node live in
# the same hash space, so the digest pair of any node can be replayed as a
# single leaf item and yield the same root — the classic second-preimage
# shape. The empty-tree sentinel below is separated by construction: no
# prefixed preimage can equal b"empty".
_LEAF_TAG = b"\x00"
_NODE_TAG = b"\x01"


def _hash_leaf(item: bytes) -> str:
    """Hash a single tree leaf into its hex digest, tagged as a leaf."""
    return hashlib.sha256(_LEAF_TAG + item).hexdigest()


def _hash_node(left: str, right: str) -> str:
    """Hash two child digests into their parent's hex digest, tagged as a node."""
    return hashlib.sha256(_NODE_TAG + (left + right).encode()).hexdigest()


def merkle_root(items: list[bytes]) -> str:
    """Compute the Merkle root of a list of byte items.

    Uses SHA-256 as the hash function. For an empty list, returns the
    hash of the string ``"empty"``. For a single item, returns the tagged
    hash of that item. Otherwise, recursively builds a binary Merkle tree.
    Leaves and internal nodes are hashed under distinct one-byte tags, so a
    node's children cannot be replayed as a leaf.

    Args:
        items: The byte strings to build the tree from.

    Returns:
        Hex-encoded SHA-256 Merkle root.
    """
    if not items:
        return hashlib.sha256(b"empty").hexdigest()
    if len(items) == 1:
        return _hash_leaf(items[0])
    mid = len(items) // 2
    return _hash_node(merkle_root(items[:mid]), merkle_root(items[mid:]))


def merkle_proof(items: list[bytes], index: int) -> MerkleProof:
    """Generate the sibling path proving ``items[index]`` is in the tree.

    Walks the same ``mid = len(items) // 2`` split that :func:`merkle_root`
    uses, so the path reconstructs that exact tree. The tree is positional,
    not sorted, so every sibling is recorded with the side it sits on.

    Args:
        items: The byte strings the tree was built from.
        index: Position of the leaf to prove, in ``range(len(items))``.

    Returns:
        The sibling path from leaf to root, as ``(sibling_digest,
        sibling_is_left)`` pairs. ``sibling_is_left`` is True when the
        sibling is the left child, so the running digest is the right one.
        A single-item tree has an empty path.

    Raises:
        IndexError: If ``index`` is outside ``range(len(items))``.
    """
    if not 0 <= index < len(items):
        raise IndexError(f"leaf index {index} out of range for {len(items)} items")
    if len(items) == 1:
        return []
    mid = len(items) // 2
    if index < mid:
        return merkle_proof(items[:mid], index) + [(merkle_root(items[mid:]), False)]
    return merkle_proof(items[mid:], index - mid) + [(merkle_root(items[:mid]), True)]


def compute_diversity(action_indices: list[int]) -> float:
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

    def __init__(self, risk_threshold: float = 0.7, diversity_min: float = 0.3):
        self.risk_threshold = risk_threshold
        self.diversity_min = diversity_min

    def validate_batch(self, proposal: BatchProposal) -> tuple[bool, str]:
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
            return False, (f"Diversity {div:.2f} below minimum {self.diversity_min}")
        root = merkle_root([str(i).encode() for i in proposal.action_indices])
        return True, f"Batch valid. Root: {root[:16]}..."

    def verify_proof(self, action_index: int, proof: MerkleProof, root: str) -> bool:
        """Verify a Merkle proof for a single action within a batch.

        :func:`merkle_root` builds internal nodes positionally, so each
        sibling is recombined on the side it was generated from. Sorting the
        pair instead discards that side, and reproduces the positional tree
        only at a node whose left child's digest already sorts below its
        right's — a coin flip per level, so a sorted verifier still accepts
        roughly ``2 ** -depth`` of all honest paths: about half of a two-leaf
        tree, a vanishing fraction as the batch grows. It is that coincidence,
        not correctness, that let a hand-built golden pass against a verifier
        which could not verify.

        Args:
            action_index: The action to verify. Its leaf is derived the same
                way :meth:`validate_batch` derives it, from ``str(index)``.
            proof: The sibling path from :func:`merkle_proof`, leaf to root,
                as ``(sibling_digest, sibling_is_left)`` pairs.
            root: The expected Merkle root.

        Returns:
            True if the path reconstructs ``root``.
        """
        current = _hash_leaf(str(action_index).encode())
        for sibling, sibling_is_left in proof:
            if sibling_is_left:
                current = _hash_node(sibling, current)
            else:
                current = _hash_node(current, sibling)
        return current == root
