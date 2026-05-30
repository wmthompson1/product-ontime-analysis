"""
Manufacturing Graph — Schema Model v0.0.1
==========================================
Defines the **Structural Containment** layer of the manufacturing ArangoDB graph.

Architecture
------------
The graph is separated into two layers that are intentionally decoupled:

Physical (structural) layer — this module
    Mirrors the on-premise ERP catalog schema.
    No business meaning is embedded here; just topology.

        tables ──[contains]──> columns

Semantic layer — graph_sync.py / existing collections
    Maps analytical intent to abstract concepts and approved SQL snippets.

        intents ──[elevates]──> concepts
        intents ──[bound_to]──> bindings
        + Perspective_Intents / Perspective_Concepts bridge documents

Multi-tiered traversal for Text-to-SQL agents
----------------------------------------------
A resolver can walk:
    tables/{table} -[contains]-> columns/{table}__{col}
                                 -[CAN_MEAN]-> concepts/{concept}
                                               <-[elevates]- intents/{intent}
                                               <-[BOUND_TO]- bindings/{binding_key}

Key conventions
---------------
- Table vertex key  : ``table_name``  (e.g. ``corrective_actions``)
- Column vertex key : ``{table_name}__{column_name}``  (double-underscore separator;
  ArangoDB _key cannot contain a dot)
- Contains edge key : same as column key (one parent per column, so the key is unique)

Collections introduced by this model
-------------------------------------
- ``tables``   — vertex collection
- ``columns``  — vertex collection
- ``contains`` — edge collection  (from: tables, to: columns)
"""

from __future__ import annotations
from typing import Any, Dict

# ── Collection name constants ────────────────────────────────────────────────

TABLES_COLLECTION: str = "tables"
COLUMNS_COLLECTION: str = "columns"
CONTAINS_EDGE_COLLECTION: str = "contains"

# ── Edge definition for the named graph ─────────────────────────────────────

CONTAINS_EDGE_DEFINITION: Dict[str, Any] = {
    "edge_collection": CONTAINS_EDGE_COLLECTION,
    "from_vertex_collections": [TABLES_COLLECTION],
    "to_vertex_collections": [COLUMNS_COLLECTION],
}

# ── Key helpers ──────────────────────────────────────────────────────────────

def column_key(table_name: str, column_name: str) -> str:
    """Return the ArangoDB ``_key`` for a column vertex.

    Uses a double-underscore separator because ArangoDB ``_key`` values
    cannot contain a dot character.

    Example::

        column_key("corrective_actions", "capa_id")
        # → "corrective_actions__capa_id"
    """
    return f"{table_name}__{column_name}"


def contains_edge_key(table_name: str, column_name: str) -> str:
    """Return the ArangoDB ``_key`` for a contains edge.

    Each column has exactly one parent table, so the column key doubles as the
    edge key.
    """
    return column_key(table_name, column_name)


# ── Document builders ────────────────────────────────────────────────────────

def table_vertex(
    table_name: str,
    description: str = "",
    synced_at: str = "",
) -> Dict[str, Any]:
    """Build a ``tables`` vertex document ready for ArangoDB insert/update."""
    return {
        "_key": table_name,
        "table_name": table_name,
        "qualified_name": f"dbo.{table_name.upper()}",
        "description": description,
        "node_type": "table",
        "synced_at": synced_at,
    }


def column_vertex(
    table_name: str,
    column_name: str,
    data_type: str = "",
    not_null: bool = False,
    pk: bool = False,
    synced_at: str = "",
) -> Dict[str, Any]:
    """Build a ``columns`` vertex document ready for ArangoDB insert/update."""
    key = column_key(table_name, column_name)
    return {
        "_key": key,
        "table_name": table_name,
        "column_name": column_name,
        "qualified_name": f"{table_name}.{column_name}",
        "data_type": data_type,
        "not_null": not_null,
        "primary_key": pk,
        "node_type": "column",
        "synced_at": synced_at,
    }


def contains_edge(
    table_name: str,
    column_name: str,
    synced_at: str = "",
) -> Dict[str, Any]:
    """Build a ``contains`` edge document ready for ArangoDB insert/update."""
    key = contains_edge_key(table_name, column_name)
    return {
        "_key": key,
        "_from": f"{TABLES_COLLECTION}/{table_name}",
        "_to": f"{COLUMNS_COLLECTION}/{column_key(table_name, column_name)}",
        "relationship": "CONTAINS",
        "synced_at": synced_at,
    }
