#!/usr/bin/env python3
"""
Load Foreign Key Relationships as Binary Edges into ArangoDB

Reads FK relationships from schema_catalog.db and persists them
into the existing graph as FOREIGN_KEY edges.

Graph structure (additive — merges into existing semantic layer):
  - Nodes: tables (vertex collection: {ARANGO_DB}_node)
  - Edges: FOREIGN_KEY relationships (edge collection: FOREIGN_KEY)

Target graph: reads from ARANGO_DB env var (default: manufacturing_graph)
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

CATALOG_DB = os.path.join(
    os.path.dirname(__file__), '..', 'SQLMesh', 'analysis', 'impact', 'output', 'schema_catalog.db'
)

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"
EDGE_COLLECTION = "FOREIGN_KEY"


def load_fk_data():
    conn = sqlite3.connect(CATALOG_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT fk_id, from_table, from_column, to_table, to_column, fk_type, perspective
        FROM foreign_key_relationships
        ORDER BY fk_id
    """)
    fk_rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return fk_rows


def build_graph_dicts(fk_rows):
    table_set = set()
    for fk in fk_rows:
        table_set.add(fk['from_table'])
        table_set.add(fk['to_table'])

    nodes = []
    for table_name in sorted(table_set):
        nodes.append({
            "id": f"table_{table_name}",
            "table": VERTEX_COLLECTION,
            "name": table_name,
            "type": "Table",
        })

    edges = []
    for fk in fk_rows:
        edges.append({
            "from": f"table_{fk['from_table']}",
            "to": f"table_{fk['to_table']}",
            "relationship": EDGE_COLLECTION,
            "from_column": fk['from_column'],
            "to_column": fk['to_column'],
            "fk_type": fk['fk_type'],
            "perspective": fk['perspective'],
        })

    return nodes, edges


def main():
    print("=" * 70)
    print(f"Loading FK Edges into {GRAPH_NAME}")
    print("=" * 70)

    print(f"\n1. Reading FK relationships from: {CATALOG_DB}")
    fk_rows = load_fk_data()
    print(f"   Found {len(fk_rows)} FK relationships")

    print("\n2. Building graph dicts...")
    nodes, edges = build_graph_dicts(fk_rows)
    print(f"   Nodes (tables): {len(nodes)}")
    print(f"   Edges (FKs):    {len(edges)}")

    for e in edges:
        fk_label = f"{e['from']}.{e.get('from_column','')} -> {e['to']}.{e.get('to_column','')}"
        print(f"     [{e.get('fk_type',''):8s}] {fk_label}")

    print(f"\n3. Connecting to ArangoDB...")
    config = ArangoDBConfig()
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")

    persistence = ArangoDBGraphPersistence(config)

    print(f"\n4. Persisting into existing graph '{GRAPH_NAME}' (additive)...")
    stats = persistence.persist_from_dicts(
        name=GRAPH_NAME,
        nodes=nodes,
        edges=edges,
        vertex_collection=VERTEX_COLLECTION,
        edge_collection=EDGE_COLLECTION,
        overwrite=False,
        node_id_field="id",
        node_collection_field="table",
        edge_relationship_field="relationship",
        edge_from_field="from",
        edge_to_field="to",
    )

    print(f"\n5. Verifying...")
    loaded = persistence.load_graph(GRAPH_NAME)
    print(f"   Full graph: {len(loaded['nodes'])} nodes, {len(loaded['edges'])} edges")

    fk_edges = [e for e in loaded['edges'] if e.get('_collection') == EDGE_COLLECTION]
    print(f"   FOREIGN_KEY edges: {len(fk_edges)}")

    print("\n" + "=" * 70)
    print(f"SUCCESS: {stats['edges_inserted']} FK edges added to {GRAPH_NAME}")
    print(f"  {stats['nodes_inserted']} new table nodes, {stats['nodes_updated']} updated")
    print("=" * 70)

    print("\nSample AQL to traverse FK edges within the semantic layer:")
    print("-" * 70)
    print(f"""
// Find all tables reachable from 'suppliers' via FK edges
FOR v, e, p IN 1..3 INBOUND '{VERTEX_COLLECTION}/table_suppliers' {EDGE_COLLECTION}
    RETURN {{
        table: v.name,
        fk_column: e.from_column,
        perspective: e.perspective,
        depth: LENGTH(p.edges)
    }}

// Find FK path between two tables within the semantic layer
FOR p IN ANY SHORTEST_PATH
    '{VERTEX_COLLECTION}/table_non_conformant_materials'
    TO '{VERTEX_COLLECTION}/table_suppliers'
    GRAPH '{GRAPH_NAME}'
    RETURN p.vertices[*].name

// Mix FK traversal with semantic layer traversal
// FK edge to find related tables, then semantic edges for concepts
FOR v, e IN 1..1 INBOUND '{VERTEX_COLLECTION}/table_suppliers' {EDGE_COLLECTION}
    LET concepts = (
        FOR c, ce IN 1..2 OUTBOUND v._id {GRAPH_NAME}_edge
        FILTER ce.relationship IN ['CAN_MEAN', 'ELEVATES']
        RETURN c.name
    )
    RETURN {{ table: v.name, via: e.from_column, concepts: concepts }}
""")


if __name__ == "__main__":
    main()
