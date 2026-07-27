"""
In-memory implementation of :class:`~.backend.OntologyBackend`.

Used by default when no Neo4j credentials are configured. No external
dependencies. All data is ephemeral — cleared on process exit.

Real-world analogy:
    Scratch paper. Fast, convenient, no setup, but anything written on it
    is gone when you leave the room.
"""

import hashlib
import secrets
from typing import Any, Dict, List, Optional, Tuple

from .backend import OntologyBackend


class MemoryBackend(OntologyBackend):
    """Stores entities and relationships in Python dicts and lists.

    All data is held in memory. The identity vector is stored as a simple
    ``List[float]`` attribute.
    """

    def __init__(self):
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relationships: List[Tuple[str, str, str]] = []
        self._identity_vector: List[float] = []

    def _generate_id(self) -> str:
        """Generate a random 12-character hex entity ID."""
        return hashlib.sha256(secrets.token_bytes(16)).hexdigest()[:12]

    def add_entity(self, type_: str, properties: Dict[str, Any]) -> str:
        """Store a new entity. ``type_`` and ``properties`` are merged."""
        eid = self._generate_id()
        self._entities[eid] = {"id": eid, "type": type_, **properties}
        return eid

    def add_relationship(self, from_id: str, to_id: str, relation: str) -> bool:
        """Create a directed relationship. Returns False if either ID is unknown."""
        if from_id not in self._entities or to_id not in self._entities:
            return False
        self._relationships.append((from_id, to_id, relation))
        return True

    def query_relationships(self, entity_id: str) -> List[Tuple[str, str, str]]:
        """Return all relationships (outgoing and incoming) for an entity."""
        results = []
        for f, t, r in self._relationships:
            if f == entity_id:
                results.append((t, r, "outgoing"))
            if t == entity_id:
                results.append((f, r, "incoming"))
        return results

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity by ID, or None."""
        return self._entities.get(entity_id)

    def get_entities_by_type(self, type_: str) -> List[Dict[str, Any]]:
        """Filter all entities by their ``type`` field."""
        return [e for e in self._entities.values() if e.get("type") == type_]

    def get_identity_vector(self) -> List[float]:
        """Return a copy of the identity vector."""
        return list(self._identity_vector)

    def set_identity_vector(self, vector: List[float]):
        """Store a copy of the identity vector."""
        self._identity_vector = list(vector)

    def close(self):
        """Clear all data."""
        self._entities.clear()
        self._relationships.clear()
