#!/usr/bin/env python3
"""
refresh_arango_from_sqlite.py

Refresh ArangoDB from the SQLite source of truth.

Reads the semantic layer tables (schema_intents, schema_perspectives,
schema_concepts, schema_concept_fields, and their junction tables) from
SQLite and does a full overwrite into ArangoDB.

Container-agnostic:
  Works the same whether ArangoDB runs in Docker, Podman, a VM, bare
  metal, or ArangoDB Cloud.  The only requirement is that the four
  ARANGO_* environment variables point to the right host.

Environment variables:
  ARANGO_HOST            ArangoDB URL   (default: http://localhost:8529)
  ARANGO_USER            username       (default: root)
  ARANGO_ROOT_PASSWORD   password       (default: empty)
  ARANGO_DB              database name  (default: manufacturing_semantic_layer)

Safety:
  This script uses overwrite=True, which DROPS the existing named graph
  and all its collections before re-creating them from SQLite.  This is
  the correct behavior for a refresh — it guarantees ArangoDB matches
  SQLite exactly.

Usage:
  python refresh_arango_from_sqlite.py                 # default paths
  python refresh_arango_from_sqlite.py --db path/to/manufacturing.db
  python refresh_arango_from_sqlite.py --dry-run       # show counts, skip write
"""

import argparse
import os
import sqlite3
import sys
from typing import Any, Dict, List, Tuple

SQLITE_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db",
)

GRAPH_NAME = "manufacturing_semantic_layer"
VERTEX_COLLECTION = "semantic_node"
EDGE_COLLECTION = "semantic_edge"


def load_from_sqlite(db_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Read the semantic layer from SQLite and return (nodes, edges)."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    print("  Loading intents...")
    for row in conn.execute("SELECT intent_id, intent_name, intent_category, description, primary_binding_key FROM schema_intents"):
        nodes.append({
            "id": f"intent_{row['intent_name']}",
            "table": VERTEX_COLLECTION,
            "node_type": "Intent",
            "intent_id": row["intent_id"],
            "name": row["intent_name"],
            "category": row["intent_category"] or "",
            "description": row["description"] or "",
            "primary_binding_key": row["primary_binding_key"] or "",
        })

    print("  Loading perspectives...")
    for row in conn.execute("SELECT perspective_id, perspective_name, description, stakeholder_role, priority_focus FROM schema_perspectives"):
        nodes.append({
            "id": f"perspective_{row['perspective_name']}",
            "table": VERTEX_COLLECTION,
            "node_type": "Perspective",
            "perspective_id": row["perspective_id"],
            "name": row["perspective_name"],
            "description": row["description"] or "",
            "stakeholder_role": row["stakeholder_role"] or "",
            "priority_focus": row["priority_focus"] or "",
        })

    print("  Loading concepts...")
    for row in conn.execute("SELECT concept_id, concept_name, concept_type, description, domain FROM schema_concepts"):
        nodes.append({
            "id": f"concept_{row['concept_name']}",
            "table": VERTEX_COLLECTION,
            "node_type": "Concept",
            "concept_id": row["concept_id"],
            "name": row["concept_name"],
            "concept_type": row["concept_type"] or "",
            "description": row["description"] or "",
            "domain": row["domain"] or "",
        })

    print("  Loading fields...")
    for row in conn.execute("SELECT DISTINCT table_name, field_name FROM schema_concept_fields"):
        nodes.append({
            "id": f"field_{row['table_name']}_{row['field_name']}",
            "table": VERTEX_COLLECTION,
            "node_type": "Field",
            "name": f"{row['table_name']}.{row['field_name']}",
            "table_name": row["table_name"],
            "field_name": row["field_name"],
        })

    print("  Loading Intent -> Perspective edges (OPERATES_WITHIN)...")
    for row in conn.execute("""
        SELECT i.intent_name, p.perspective_name, ip.intent_factor_weight
        FROM schema_intent_perspectives ip
        JOIN schema_intents i ON ip.intent_id = i.intent_id
        JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
    """):
        edges.append({
            "from": f"intent_{row['intent_name']}",
            "to": f"perspective_{row['perspective_name']}",
            "relationship": EDGE_COLLECTION,
            "edge_type": "OPERATES_WITHIN",
            "weight": row["intent_factor_weight"],
        })

    print("  Loading Perspective -> Concept edges (USES_DEFINITION)...")
    for row in conn.execute("""
        SELECT p.perspective_name, c.concept_name, pc.priority_weight
        FROM schema_perspective_concepts pc
        JOIN schema_perspectives p ON pc.perspective_id = p.perspective_id
        JOIN schema_concepts c ON pc.concept_id = c.concept_id
    """):
        edges.append({
            "from": f"perspective_{row['perspective_name']}",
            "to": f"concept_{row['concept_name']}",
            "relationship": EDGE_COLLECTION,
            "edge_type": "USES_DEFINITION",
            "weight": row["priority_weight"],
        })

    print("  Loading Field -> Concept edges (CAN_MEAN)...")
    for row in conn.execute("""
        SELECT c.concept_name, cf.table_name, cf.field_name, cf.is_primary_meaning, cf.context_hint
        FROM schema_concept_fields cf
        JOIN schema_concepts c ON cf.concept_id = c.concept_id
    """):
        field_key = f"field_{row['table_name']}_{row['field_name']}"
        edges.append({
            "from": field_key,
            "to": f"concept_{row['concept_name']}",
            "relationship": EDGE_COLLECTION,
            "edge_type": "CAN_MEAN",
            "is_primary": row["is_primary_meaning"],
            "context_hint": row["context_hint"] or "",
        })

    print("  Loading Intent -> Concept edges (ELEVATES / SUPPRESSES / NEUTRAL)...")
    for row in conn.execute("""
        SELECT i.intent_name, c.concept_name, ic.intent_factor_weight, ic.explanation
        FROM schema_intent_concepts ic
        JOIN schema_intents i ON ic.intent_id = i.intent_id
        JOIN schema_concepts c ON ic.concept_id = c.concept_id
    """):
        weight = row["intent_factor_weight"]
        if weight == 1:
            edge_type = "ELEVATES"
        elif weight == -1:
            edge_type = "SUPPRESSES"
        else:
            edge_type = "NEUTRAL"
        edges.append({
            "from": f"intent_{row['intent_name']}",
            "to": f"concept_{row['concept_name']}",
            "relationship": EDGE_COLLECTION,
            "edge_type": edge_type,
            "weight": weight,
            "explanation": row["explanation"] or "",
        })

    conn.close()
    return nodes, edges


def print_summary(nodes: List[Dict], edges: List[Dict]):
    """Print a human-readable summary of what will be persisted."""
    type_counts: Dict[str, int] = {}
    for n in nodes:
        t = n.get("node_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    edge_type_counts: Dict[str, int] = {}
    for e in edges:
        t = e.get("edge_type", "unknown")
        edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

    print(f"\n  Nodes: {len(nodes)}")
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")
    print(f"  Edges: {len(edges)}")
    for t, c in sorted(edge_type_counts.items()):
        print(f"    {t}: {c}")


def main():
    parser = argparse.ArgumentParser(
        description="Refresh ArangoDB from SQLite source of truth"
    )
    parser.add_argument(
        "--db", default=SQLITE_DEFAULT,
        help="Path to manufacturing.db (default: auto-detect)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be written without connecting to ArangoDB"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("Refresh ArangoDB from SQLite")
    print("=" * 65)

    if not os.path.exists(args.db):
        print(f"\nError: SQLite database not found at: {args.db}")
        sys.exit(1)

    print(f"\n  SQLite: {args.db}")

    print("\nStep 1: Read semantic layer from SQLite...")
    nodes, edges = load_from_sqlite(args.db)
    print_summary(nodes, edges)

    if not nodes:
        print("\nWarning: No nodes found in SQLite. Nothing to persist.")
        sys.exit(0)

    if args.dry_run:
        print("\n--dry-run specified. Skipping ArangoDB write.")
        print("=" * 65)
        return

    print("\nStep 2: Connect to ArangoDB...")
    try:
        from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
    except ImportError:
        print("Error: arangodb_persistence module not found.")
        print("Make sure python-arango is installed: pip install python-arango")
        sys.exit(1)

    config = ArangoDBConfig()
    print(f"  Host: {config.host}")
    print(f"  Database: {config.database_name}")
    print(f"  User: {config.username}")

    persistence = ArangoDBGraphPersistence(config)

    status = persistence.test_connection()
    if not status.get("connected"):
        print(f"\nError: Cannot connect to ArangoDB: {status.get('error')}")
        print("\nTroubleshooting:")
        print("  1. Is ArangoDB running?")
        print("  2. Check ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB")
        print("  3. For Docker: ensure the container is started and port 8529 is mapped")
        print("  4. For cloud: ensure the database was pre-created in the console")
        sys.exit(1)

    print(f"  Connected (ArangoDB {status.get('version', 'unknown')})")
    existing = status.get("graphs", [])
    if GRAPH_NAME in existing:
        print(f"  Existing graph '{GRAPH_NAME}' will be REPLACED (overwrite=True)")

    print(f"\nStep 3: Persist to ArangoDB (overwrite=True)...")
    stats = persistence.persist_from_dicts(
        name=GRAPH_NAME,
        nodes=nodes,
        edges=edges,
        vertex_collection=VERTEX_COLLECTION,
        edge_collection=EDGE_COLLECTION,
        overwrite=True,
    )

    print(f"\nStep 4: Verify by loading back...")
    loaded = persistence.load_graph(name=GRAPH_NAME)
    print(f"  Verified: {len(loaded['nodes'])} nodes, {len(loaded['edges'])} edges")

    print("\n" + "=" * 65)
    print("SUCCESS: ArangoDB refreshed from SQLite")
    print("=" * 65)
    print(f"\n  Graph: {GRAPH_NAME}")
    print(f"  Nodes inserted: {stats['nodes_inserted']}")
    print(f"  Nodes updated:  {stats['nodes_updated']}")
    print(f"  Edges inserted: {stats['edges_inserted']}")
    print(f"\n  View in ArangoDB web UI: {config.host}")
    print(f"  AQL: FOR doc IN {VERTEX_COLLECTION} LIMIT 10 RETURN doc")


if __name__ == "__main__":
    main()
