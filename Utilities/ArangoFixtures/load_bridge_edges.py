#!/usr/bin/env python3
"""
Load MAPS_TO_CONCEPT Bridge Edges into ArangoDB

Reads table-to-concept field mappings from manufacturing.db (schema_concept_fields)
and persists them as MAPS_TO_CONCEPT edges into the manufacturing_graph,
bridging Table nodes to Concept nodes in the semantic layer.

Graph structure (additive):
  - From: Table nodes (vertex collection: {ARANGO_DB}_node)
  - To: Concept nodes (vertex collection: {ARANGO_DB}_node)
  - Edge collection: MAPS_TO_CONCEPT

Target graph: reads from ARANGO_DB env var (default: manufacturing_graph)
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
from arango import ArangoClient

MANUFACTURING_DB = os.path.join(
    os.path.dirname(__file__), '..', '..', 'hf-space-inventory-sqlgen', 'app_schema', 'manufacturing.db'
)

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"
EDGE_COLLECTION = "MAPS_TO_CONCEPT"


def load_concept_field_mappings():
    conn = sqlite3.connect(MANUFACTURING_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT cf.table_name, cf.field_name, cf.is_primary_meaning, cf.context_hint,
               c.concept_name
        FROM schema_concept_fields cf
        JOIN schema_concepts c ON cf.concept_id = c.concept_id
    ''')
    mappings = [dict(r) for r in cursor]
    conn.close()
    return mappings


def main():
    print("=" * 70)
    print(f"Loading Bridge Edges into {GRAPH_NAME}")
    print("=" * 70)

    mappings = load_concept_field_mappings()
    print(f"\n1. Found {len(mappings)} table-to-concept mappings from SQLite")

    config = ArangoDBConfig()
    client = ArangoClient(hosts=config.host)
    db = client.db(config.database_name, username=config.username, password=config.password)

    print(f"\n2. Connecting to ArangoDB...")
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")

    if not db.has_collection(EDGE_COLLECTION):
        db.create_collection(EDGE_COLLECTION, edge=True)
        print(f"   Created edge collection: {EDGE_COLLECTION}")

    graph = db.graph(GRAPH_NAME)
    existing_edge_defs = [e['edge_collection'] for e in graph.edge_definitions()]
    if EDGE_COLLECTION not in existing_edge_defs:
        graph.create_edge_definition(
            edge_collection=EDGE_COLLECTION,
            from_vertex_collections=[VERTEX_COLLECTION],
            to_vertex_collections=[VERTEX_COLLECTION]
        )
        print(f"   Registered {EDGE_COLLECTION} in graph edge definitions")

    print(f"\n3. Inserting bridge edges (additive)...")
    ecol = db.collection(EDGE_COLLECTION)
    inserted = 0
    skipped = 0
    tables_linked = set()

    for m in mappings:
        table_key = f"table_{m['table_name']}"
        concept_key = f"{VERTEX_COLLECTION}_concept_{m['concept_name']}"
        from_id = f"{VERTEX_COLLECTION}/{table_key}"
        to_id = f"{VERTEX_COLLECTION}/{concept_key}"

        edge_doc = {
            '_from': from_id,
            '_to': to_id,
            'field_name': m['field_name'],
            'is_primary_meaning': bool(m['is_primary_meaning']),
            'context_hint': m['context_hint'],
            'relationship': EDGE_COLLECTION,
        }
        try:
            ecol.insert(edge_doc)
            inserted += 1
            tables_linked.add(m['table_name'])
            fk_type = '*' if m['is_primary_meaning'] else ' '
            print(f"     {fk_type} {m['table_name']}.{m['field_name']} -> {m['concept_name']}")
        except Exception as e:
            skipped += 1

    print(f"\n4. Results:")
    print(f"   Inserted: {inserted}, Skipped: {skipped}")
    print(f"   Tables linked: {sorted(tables_linked)}")
    print(f"   Total {EDGE_COLLECTION} edges: {ecol.count()}")

    print(f"\n{'=' * 70}")
    print(f"SUCCESS: {inserted} bridge edges added to {GRAPH_NAME}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
