"""
Neo4j Aura implementation of :class:`~.backend.OntologyBackend`.

Connects to a Neo4j Aura graph database instance. Credentials are loaded
from ``.env`` in the project root:

- ``NEO4J_URI`` — e.g. ``neo4j+s://your-instance.databases.neo4j.io``
- ``NEO4J_USER`` (or ``NEO4J_USERNAME``) — default: ``neo4j``
- ``NEO4J_PASSWORD`` — your database password

Falls back to environment variables if ``.env`` is absent.

Real-world analogy:
    Upgrading from a local notebook (MemoryBackend) to a shared database
    server (Neo4j Aura). The queries (methods) stay the same; only the
    storage engine changes.
"""

import json
import os
from typing import Any

try:
    from neo4j import Driver, GraphDatabase, Session  # noqa: F401

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import certifi

    CERTIFI_AVAILABLE = True
except ImportError:
    CERTIFI_AVAILABLE = False

from .backend import OntologyBackend


def _load_env() -> dict[str, str]:
    """Load Neo4j credentials from ``.env`` or environment variables."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"
    )
    result = {
        "NEO4J_URI": os.environ.get("NEO4J_URI", ""),
        "NEO4J_USER": os.environ.get("NEO4J_USER", os.environ.get("NEO4J_USERNAME", "")),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", ""),
    }
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    val = v.strip().strip('"').strip("'")
                    if k == "NEO4J_USERNAME":
                        if not result["NEO4J_USER"]:
                            result["NEO4J_USER"] = val
                    elif k in result and not result[k]:
                        result[k] = val
    return result


class Neo4jBackend(OntologyBackend):
    """Neo4j Aura graph-database backend for the Governance Layer ontology.

    Entities are stored as labelled ``:Entity`` nodes with a ``properties``
    JSON attribute. Relationships are stored as ``[:RELATES]`` edges with
    a ``type`` property. The identity vector is stored as a single
    ``:Identity`` node with ``name: 'vector'``.

    Args:
        uri: Neo4j connection URI (default: from environment).
        user: Username (default: from environment).
        password: Password (default: from environment).

    Raises:
        ImportError: If the ``neo4j`` driver is not installed.
        ValueError: If no URI is configured.
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j driver not installed. Install with: uv sync")

        env = _load_env()
        self._uri = uri or env["NEO4J_URI"]
        self._user = user or env["NEO4J_USER"]
        self._password = password or env["NEO4J_PASSWORD"]

        if not self._uri:
            raise ValueError("Neo4j URI not configured. Set NEO4J_URI in .env or environment.")

        if CERTIFI_AVAILABLE:
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())

        self._driver: Driver = GraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )

    def _run(self, query: str, params: dict = None) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts."""
        with self._driver.session() as session:
            result = session.run(query, params or {})
            return [dict(r) for r in result]

    def add_entity(self, type_: str, properties: dict[str, Any]) -> str:
        """Create a new ```:Entity`` node and return its element ID."""
        props_json = json.dumps(properties)
        query = "CREATE (e:Entity {type: $type, properties: $props}) RETURN elementId(e) AS id"
        result = self._run(query, {"type": type_, "props": props_json})
        return result[0]["id"] if result else ""

    def add_relationship(self, from_id: str, to_id: str, relation: str) -> bool:
        """Link two nodes with a ```[:RELATES]`` edge."""
        query = (
            "MATCH (a), (b) WHERE elementId(a) = $from_id AND elementId(b) = $to_id "
            "CREATE (a)-[r:RELATES {type: $relation}]->(b) "
            "RETURN count(r) AS cnt"
        )
        result = self._run(query, {"from_id": from_id, "to_id": to_id, "relation": relation})
        return result[0]["cnt"] > 0 if result else False

    def query_relationships(self, entity_id: str) -> list[tuple[str, str, str]]:
        """Return all relationships (outgoing + incoming) for a node."""
        query = (
            "MATCH (a)-[r]->(b) WHERE elementId(a) = $eid "
            "RETURN elementId(b) AS target, r.type AS relation, 'outgoing' AS direction "
            "UNION "
            "MATCH (a)<-[r]-(b) WHERE elementId(a) = $eid "
            "RETURN elementId(b) AS target, r.type AS relation, 'incoming' AS direction"
        )
        result = self._run(query, {"eid": entity_id})
        return [(r["target"], r["relation"], r["direction"]) for r in result]

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve a single entity node by element ID."""
        query = (
            "MATCH (e) WHERE elementId(e) = $eid "
            "RETURN e.type AS type, e.properties AS props, elementId(e) AS id"
        )
        result = self._run(query, {"eid": entity_id})
        if not result:
            return None
        r = result[0]
        entity = {"id": r["id"], "type": r["type"]}
        if r.get("props"):
            entity.update(json.loads(r["props"]))
        return entity

    def get_entities_by_type(self, type_: str) -> list[dict[str, Any]]:
        """Retrieve all entities of a given type."""
        query = (
            "MATCH (e:Entity) WHERE e.type = $type "
            "RETURN e.type AS type, e.properties AS props, elementId(e) AS id"
        )
        result = self._run(query, {"type": type_})
        entities = []
        for r in result:
            entity = {"id": r["id"], "type": r["type"]}
            if r.get("props"):
                entity.update(json.loads(r["props"]))
            entities.append(entity)
        return entities

    def get_identity_vector(self) -> list[float]:
        """Retrieve the latest identity vector from the ``:Identity`` node."""
        query = (
            "MATCH (v:Identity) WHERE v.name = 'vector' "
            "RETURN v.values AS values ORDER BY v.updated_at DESC LIMIT 1"
        )
        result = self._run(query)
        if result and result[0].get("values"):
            return json.loads(result[0]["values"])
        return []

    def set_identity_vector(self, vector: list[float]):
        """Upsert the identity vector on the ``:Identity`` node."""
        vec_json = json.dumps(vector)
        query = (
            "MERGE (v:Identity {name: 'vector'}) SET v.values = $values, v.updated_at = timestamp()"
        )
        self._run(query, {"values": vec_json})

    def close(self):
        """Close the Neo4j driver connection."""
        self._driver.close()
