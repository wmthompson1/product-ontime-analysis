#!/usr/bin/env python3
"""
Persist Semantic Graph to ArangoDB

Exports the manufacturing semantic layer from SQLite to ArangoDB.
Graph structure: Intent -> Perspective -> Concept <- Field

Direct python-arango implementation (no NetworkX dependency).
"""

import os
import sqlite3
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

SQLITE_PATH = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"


def load_semantic_nodes_and_edges(conn):
    """Load the semantic graph from SQLite into plain dicts."""
    graph_name = os.getenv("ARANGO_DB", "manufacturing_graph")
    COLLECTION = f"{graph_name}_node"

    nodes = []
    edges = []

    print("Loading intents...")
    cursor = conn.execute("SELECT intent_id, intent_name, description FROM schema_intents")
    for row in cursor:
        node_key = f"intent_{row['intent_name']}"
        nodes.append({
            "id": f"{COLLECTION}/{node_key}",
            "table": COLLECTION,
            "type": "Intent",
            "intent_id": row['intent_id'],
            "name": row['intent_name'],
            "description": row['description'] or "",
        })

    print("Loading perspectives...")
    cursor = conn.execute("SELECT perspective_id, perspective_name, description FROM schema_perspectives")
    for row in cursor:
        node_key = f"perspective_{row['perspective_name']}"
        nodes.append({
            "id": f"{COLLECTION}/{node_key}",
            "table": COLLECTION,
            "type": "Perspective",
            "perspective_id": row['perspective_id'],
            "name": row['perspective_name'],
            "description": row['description'] or "",
        })

    print("Loading concepts...")
    cursor = conn.execute("SELECT concept_id, concept_name, description FROM schema_concepts")
    for row in cursor:
        node_key = f"concept_{row['concept_name']}"
        nodes.append({
            "id": f"{COLLECTION}/{node_key}",
            "table": COLLECTION,
            "type": "Concept",
            "concept_id": row['concept_id'],
            "name": row['concept_name'],
            "description": row['description'] or "",
        })

    print("Loading fields...")
    cursor = conn.execute("SELECT DISTINCT table_name, field_name FROM schema_concept_fields")
    for row in cursor:
        node_key = f"field_{row['table_name']}_{row['field_name']}"
        nodes.append({
            "id": f"{COLLECTION}/{node_key}",
            "table": COLLECTION,
            "type": "Field",
            "table_name": row['table_name'],
            "field_name": row['field_name'],
            "name": f"{row['table_name']}.{row['field_name']}",
        })

    print("Loading Intent -> Perspective edges...")
    cursor = conn.execute("""
        SELECT i.intent_name, p.perspective_name, ip.intent_factor_weight
        FROM schema_intent_perspectives ip
        JOIN schema_intents i ON ip.intent_id = i.intent_id
        JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
    """)
    for row in cursor:
        edges.append({
            "from": f"{COLLECTION}/intent_{row['intent_name']}",
            "to": f"{COLLECTION}/perspective_{row['perspective_name']}",
            "relationship": "OPERATES_WITHIN",
            "weight": row['intent_factor_weight'],
        })

    print("Loading Perspective -> Concept edges...")
    cursor = conn.execute("""
        SELECT p.perspective_name, c.concept_name
        FROM schema_perspective_concepts pc
        JOIN schema_perspectives p ON pc.perspective_id = p.perspective_id
        JOIN schema_concepts c ON pc.concept_id = c.concept_id
    """)
    for row in cursor:
        edges.append({
            "from": f"{COLLECTION}/perspective_{row['perspective_name']}",
            "to": f"{COLLECTION}/concept_{row['concept_name']}",
            "relationship": "USES_DEFINITION",
        })

    print("Loading Field -> Concept edges...")
    cursor = conn.execute("""
        SELECT c.concept_name, cf.table_name, cf.field_name
        FROM schema_concept_fields cf
        JOIN schema_concepts c ON cf.concept_id = c.concept_id
    """)
    for row in cursor:
        field_key = f"field_{row['table_name']}_{row['field_name']}"
        edges.append({
            "from": f"{COLLECTION}/{field_key}",
            "to": f"{COLLECTION}/concept_{row['concept_name']}",
            "relationship": "CAN_MEAN",
        })

    print("Loading Intent -> Concept edges...")
    cursor = conn.execute("""
        SELECT i.intent_name, c.concept_name, ic.intent_factor_weight
        FROM schema_intent_concepts ic
        JOIN schema_intents i ON ic.intent_id = i.intent_id
        JOIN schema_concepts c ON ic.concept_id = c.concept_id
    """)
    for row in cursor:
        weight = row['intent_factor_weight']
        if weight == 1:
            rel = "ELEVATES"
        elif weight == -1:
            rel = "SUPPRESSES"
        else:
            rel = "NEUTRAL"
        edges.append({
            "from": f"{COLLECTION}/intent_{row['intent_name']}",
            "to": f"{COLLECTION}/concept_{row['concept_name']}",
            "relationship": rel,
            "weight": weight,
        })

    return nodes, edges


def main():
    print("=" * 60)
    print("Semantic Graph -> ArangoDB Persistence")
    print("=" * 60)

    print("\nLoading semantic graph from SQLite...")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    nodes, edges = load_semantic_nodes_and_edges(conn)
    conn.close()

    print(f"\nGraph Statistics:")
    print(f"   Nodes: {len(nodes)}")
    print(f"   Edges: {len(edges)}")

    type_counts = {}
    for n in nodes:
        t = n.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"   Node types: {type_counts}")

    rel_counts = {}
    for e in edges:
        r = e.get('relationship', 'unknown')
        rel_counts[r] = rel_counts.get(r, 0) + 1
    print(f"   Edge types: {rel_counts}")

    print("\nConnecting to ArangoDB...")
    config = ArangoDBConfig()
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")

    persistence = ArangoDBGraphPersistence(config)

    print("\nPersisting graph to ArangoDB...")
    graph_name = os.getenv("ARANGO_DB", "manufacturing_graph")
    vertex_collection = f"{graph_name}_node"

    stats = persistence.persist_from_dicts(
        name=graph_name,
        nodes=nodes,
        edges=edges,
        vertex_collection=vertex_collection,
        edge_collection=f"{graph_name}_edge",
        overwrite=False,
        edge_relationship_field="_no_routing_",
    )

    print(f"\nGraph persisted successfully! Stats: {stats}")

    print("\nVerifying persistence by loading back...")
    loaded = persistence.load_graph(name=graph_name)
    print(f"   Loaded nodes: {len(loaded['nodes'])}")
    print(f"   Loaded edges: {len(loaded['edges'])}")

    print("\n" + "=" * 60)
    print("SUCCESS: Semantic graph persisted to ArangoDB!")
    print("=" * 60)
    print("\nYou can now view your graph at:")
    print(f"   {config.host}")
    print("\nAQL query to explore:")
    print(f'   FOR doc IN {vertex_collection} LIMIT 10 RETURN doc')


if __name__ == "__main__":
    main()
