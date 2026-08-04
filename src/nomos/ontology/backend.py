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
from typing import Any


class OntologyBackend(ABC):
    """Abstract interface for entity-relationship storage.

    Mimics a graph database with entities (nodes) and relationships (edges),
    plus identity-vector storage for the Identity Layer.
    """

    @abstractmethod
    def add_entity(self, type_: str, properties: dict[str, Any]) -> str:
        """Store a new entity and return its ID."""

    @abstractmethod
    def add_relationship(self, from_id: str, to_id: str, relation: str) -> bool:
        """Link two entities with a named relationship."""

    @abstractmethod
    def query_relationships(self, entity_id: str) -> list[tuple[str, str, str]]:
        """Return all relationships for an entity (incoming and outgoing).

        Returns:
            List of ``(target_id, relation_name, direction)`` tuples.
        """

    @abstractmethod
    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity by its ID, or None if not found."""

    @abstractmethod
    def get_entities_by_type(self, type_: str) -> list[dict[str, Any]]:
        """Retrieve all entities of a given type."""

    @abstractmethod
    def get_identity_vector(self) -> list[float]:
        """Retrieve the stored identity vector."""

    @abstractmethod
    def set_identity_vector(self, vector: list[float]):
        """Persist the identity vector."""

    @abstractmethod
    def close(self):
        """Release any backend resources (connections, file handles)."""

    def ping(self) -> bool:
        """Check whether the backend is reachable right now.

        Used by the ``/readyz`` health endpoint (see ``server.py``). The
        default implementation always returns ``True`` — in-process
        backends with no external dependency (e.g. :class:`MemoryBackend`)
        are reachable by definition. Backends with a real network
        connection (e.g. :class:`Neo4jBackend`) override this.
        """
        return True
