"""
Abstract interface for ontology storage backends (Chapter 4 §1).

Two implementations:

- :class:`~.memory_backend.MemoryBackend`: In-memory dicts, no external
  dependencies, used by default.
- :class:`~.neo4j_backend.Neo4jBackend`: Cypher queries to a Neo4j Aura
  instance for persistent storage.

Governance code never imports Neo4j directly. It only talks to this ABC.

Real-world analogy:
    A database abstraction layer in an ORM. The application code writes
    against the interface; the actual storage (SQLite, PostgreSQL, etc.)
    is a deployment detail.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class OntologyBackend(ABC):
    """Abstract interface for entity-relationship storage.

    Mimics a graph database with entities (nodes) and relationships (edges),
    plus identity-vector storage for the Identity Layer.
    """

    @abstractmethod
    def add_entity(self, type_: str, properties: Dict[str, Any]) -> str:
        """Store a new entity and return its ID."""

    @abstractmethod
    def add_relationship(self, from_id: str, to_id: str, relation: str) -> bool:
        """Link two entities with a named relationship."""

    @abstractmethod
    def query_relationships(self, entity_id: str) -> List[Tuple[str, str, str]]:
        """Return all relationships for an entity (incoming and outgoing).

        Returns:
            List of ``(target_id, relation_name, direction)`` tuples.
        """

    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entity by its ID, or None if not found."""

    @abstractmethod
    def get_entities_by_type(self, type_: str) -> List[Dict[str, Any]]:
        """Retrieve all entities of a given type."""

    @abstractmethod
    def get_identity_vector(self) -> List[float]:
        """Retrieve the stored identity vector."""

    @abstractmethod
    def set_identity_vector(self, vector: List[float]):
        """Persist the identity vector."""

    @abstractmethod
    def close(self):
        """Release any backend resources (connections, file handles)."""
