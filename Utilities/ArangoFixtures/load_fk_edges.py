#!/usr/bin/env python3
"""
Load Foreign Key Relationships as Binary Edges into ArangoDB

Reads FK relationships from schema_catalog.db and persists them
as a graph in ArangoDB using persist_from_dicts().

Graph structure:
  - Nodes: tables (one node per table involved in an FK)
  - Edges: FOREIGN_KEY relationships (binary: from_table -> to_table)

Target database: manufacturing_schema (from ARANGO_DB env var)
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

CATALOG_DB = os.path.join(
    os.path.dirname(__file__), '..', 'SQLMesh', 'analysis', 'impact', 'output', 'schema_catalog.db'
)

GRAPH_NAME = "manufacturing_fk_graph"


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
            "id": table_name,
            "table": "schema_tables",
            "name": table_name,
            "type": "Table",
        })

    edges = []
    for fk in fk_rows:
        edges.append({
            "from": fk['from_table'],
            "to": fk['to_table'],
            "relationship": "FOREIGN_KEY",
            "from_column": fk['from_column'],
            "to_column": fk['to_column'],
            "fk_type": fk['fk_type'],
            "perspective": fk['perspective'],
        })

    return nodes, edges


def main():
    print("=" * 70)
    print("Loading FK Edges into ArangoDB")
    print("=" * 70)

    print(f"\n1. Reading FK relationships from: {CATALOG_DB}")
    fk_rows = load_fk_data()
    print(f"   Found {len(fk_rows)} FK relationships")

    print("\n2. Building graph dicts...")
    nodes, edges = build_graph_dicts(fk_rows)
    print(f"   Nodes (tables): {len(nodes)}")
    print(f"   Edges (FKs):    {len(edges)}")

    for e in edges:
        fk_label = f"{e['from']}.{e['from_column']} -> {e['to']}.{e['to_column']}"
        print(f"     [{e['fk_type']:8s}] {fk_label}")

    print(f"\n3. Connecting to ArangoDB...")
    config = ArangoDBConfig()
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")

    persistence = ArangoDBGraphPersistence(config)

    print(f"\n4. Persisting graph '{GRAPH_NAME}'...")
    stats = persistence.persist_from_dicts(
        name=GRAPH_NAME,
        nodes=nodes,
        edges=edges,
        vertex_collection="schema_tables",
        edge_collection="FOREIGN_KEY",
        overwrite=True,
        node_id_field="id",
        node_collection_field="table",
        edge_relationship_field="relationship",
        edge_from_field="from",
        edge_to_field="to",
    )

    print(f"\n5. Verifying...")
    loaded = persistence.load_graph(GRAPH_NAME)
    print(f"   Loaded: {len(loaded['nodes'])} nodes, {len(loaded['edges'])} edges")

    print("\n" + "=" * 70)
    print(f"SUCCESS: {GRAPH_NAME} loaded into ArangoDB")
    print(f"  {stats['nodes_inserted']} table nodes, {stats['edges_inserted']} FK edges")
    print("=" * 70)

    print("\nSample AQL to traverse FK graph:")
    print("-" * 70)
    print("""
// Find all tables reachable from 'suppliers' via FK edges
FOR v, e, p IN 1..3 INBOUND 'schema_tables/suppliers' FOREIGN_KEY
    RETURN {
        table: v.name,
        fk_column: e.from_column,
        perspective: e.perspective,
        depth: LENGTH(p.edges)
    }

// Find all FK paths between two tables
FOR p IN ANY SHORTEST_PATH
    'schema_tables/non_conformant_materials' TO 'schema_tables/suppliers'
    GRAPH 'manufacturing_fk_graph'
    RETURN p.vertices[*].name
""")


if __name__ == "__main__":
    main()
