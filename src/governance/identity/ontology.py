"""
Formal action namespace :math:`\\mathcal{O}` with runtime integrity hashes (Chapter 4 §1).

The ontology binds each action index to its operational semantics and a
runtime integrity hash. The TEE verifies at batch validation time that the
current runtime implementation matches the genesis commitment.

This is the defence against semantic drift: if an implementation changes
without a corresponding ontology update, the runtime hash will mismatch
and the TEE will reject the batch.

Real-world analogy:
    A pharmacopoeia — an official catalogue of approved drugs, each with
    a chemical formula, dosage, and quality standard. Any deviation from
    the standard is a violation, even if the drug's name stays the same.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class ActionBinding:
    """A frozen record binding an action index to its runtime implementation.

    Attributes:
        index: The action's unique numeric identifier.
        operation: Human-readable description of the action's semantics.
        runtime_hash: SHA-256 hash of the implementation bytes, used to
            verify runtime integrity against the genesis commitment.
        properties: Named scalar features of the action (e.g. expected
            reward range, risk profile, identity relevance).
    """

    index: int
    operation: str
    runtime_hash: str
    properties: Dict[str, float]


def compute_hash(implementation_bytes: bytes) -> str:
    """Compute the SHA-256 integrity hash of an action implementation.

    Args:
        implementation_bytes: The bytecode or source bytes of the
            action's implementation function.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(implementation_bytes).hexdigest()


class Ontology:
    """The formal action namespace :math:`\\mathcal{O}`.

    Every action the agent can perform must be registered here before
    it can be proposed or voted on. The ontology enforces that:

    - No two actions share an index (unique binding)
    - Every action has an integrity hash traceable to genesis
    - The registry is append-only (no deletion, only extension)
    """

    def __init__(self):
        self._bindings: Dict[int, ActionBinding] = {}
        self._append_only_log: List[ActionBinding] = []

    def register(self, index: int, operation: str,
                 implementation_bytes: bytes,
                 properties: Dict[str, float]) -> ActionBinding:
        """Bind an action index to its implementation and properties.

        Args:
            index: Unique action identifier. Must not already be bound.
            operation: Human-readable description.
            implementation_bytes: Source or bytecode for integrity hashing.
            properties: Metadata for Parliament members' value functions.

        Returns:
            The newly created :class:`ActionBinding`.

        Raises:
            ValueError: If ``index`` is already registered.
        """
        if index in self._bindings:
            raise ValueError(f"Action index {index} already bound")
        h = compute_hash(implementation_bytes)
        binding = ActionBinding(
            index=index,
            operation=operation,
            runtime_hash=h,
            properties=properties,
        )
        self._bindings[index] = binding
        self._append_only_log.append(binding)
        return binding

    def verify_binding(self, index: int,
                       runtime_implementation: bytes) -> bool:
        """Verify that a runtime implementation matches the registered hash.

        If this returns False, the implementation has drifted from what
        was registered — the TEE should reject the batch.

        Args:
            index: The action to verify.
            runtime_implementation: The current implementation bytes.

        Returns:
            True if the hash matches the registered binding.
        """
        if index not in self._bindings:
            return False
        expected = self._bindings[index].runtime_hash
        actual = compute_hash(runtime_implementation)
        return actual == expected

    def get_properties(self, index: int) -> Optional[Dict[str, float]]:
        """Get the registered properties for an action.

        Args:
            index: The action to look up.

        Returns:
            A copy of the properties dict, or None if not found.
        """
        binding = self._bindings.get(index)
        if binding is None:
            return None
        return dict(binding.properties)

    def has_index(self, index: int) -> bool:
        """Check whether an action index is registered.

        Args:
            index: The action index.

        Returns:
            True if registered.
        """
        return index in self._bindings

    @property
    def size(self) -> int:
        """Number of registered actions."""
        return len(self._bindings)

    def __repr__(self):
        return f"<Ontology {self.size} actions>"
