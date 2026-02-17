#!/usr/bin/env python3
"""
Verify ArangoDB Manufacturing Graph Integrity

Asserts:
  1. ARANGO_DB env var is set and matches DATABASE_NAME
  2. All expected edge collections are registered in the named graph
  3. 100% of table nodes are reachable to semantic layer via hybrid traversal

Exit code 0 = pass, 1 = fail
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from arangodb_persistence import ArangoDBConfig
from arango import ArangoClient


def main():
    errors = []

    arango_db = os.getenv("ARANGO_DB")
    database_name = os.getenv("DATABASE_NAME")
    if not arango_db:
        errors.append("ARANGO_DB env var is not set")
    if database_name and arango_db and arango_db != database_name:
        errors.append(f"ARANGO_DB ({arango_db}) != DATABASE_NAME ({database_name})")

    print("=" * 70)
    print("ArangoDB Manufacturing Graph Verification")
    print("=" * 70)
    print(f"  ARANGO_DB: {arango_db}")
    print(f"  DATABASE_NAME: {database_name}")

    config = ArangoDBConfig()
    client = ArangoClient(hosts=config.host)

    try:
        db = client.db(config.database_name, username=config.username, password=config.password)
    except Exception as e:
        errors.append(f"Cannot connect to ArangoDB: {e}")
        _report(errors)
        return

    graph_name = arango_db or "manufacturing_graph"
    if not db.has_graph(graph_name):
        errors.append(f"Graph '{graph_name}' does not exist")
        _report(errors)
        return

    graph = db.graph(graph_name)
    edge_defs = [e['edge_collection'] for e in graph.edge_definitions()]
    print(f"\n  Graph: {graph_name}")
    print(f"  Edge definitions: {edge_defs}")

    expected_edges = ['CAN_MEAN', 'ELEVATES', 'FOREIGN_KEY', 'MAPS_TO_CONCEPT',
                      'NEUTRAL', 'OPERATES_WITHIN', 'USES_DEFINITION']
    missing = [e for e in expected_edges if e not in edge_defs]
    if missing:
        errors.append(f"Missing edge definitions: {missing}")

    vcol = db.collection(f"{graph_name}_node")
    node_count = vcol.count()
    print(f"  Nodes: {node_count}")
    for ecol_name in edge_defs:
        ecol = db.collection(ecol_name)
        print(f"    {ecol_name}: {ecol.count()} edges")

    print(f"\n  Hybrid Traversal (depth 1..3):")
    cursor = db.aql.execute('''
        FOR t IN manufacturing_graph_node
            FILTER t.type == "Table"
            LET semantic = (
                FOR v IN 1..3 ANY t GRAPH "manufacturing_graph"
                    FILTER v.type IN ["Concept", "Intent", "Perspective", "Field"]
                    RETURN DISTINCT v.type
            )
            RETURN {table: t.name, linked: LENGTH(UNIQUE(semantic)) > 0}
    ''')
    results = [r for r in cursor]
    linked = sum(1 for r in results if r['linked'])
    total = len(results)
    pct = 100 * linked / total if total else 0
    print(f"    Tables linked: {linked}/{total} ({pct:.0f}%)")

    orphans = [r['table'] for r in results if not r['linked']]
    if orphans:
        errors.append(f"Orphan tables (not linked to semantic layer): {orphans}")

    for r in sorted(results, key=lambda x: x['table']):
        status = "PASS" if r['linked'] else "FAIL"
        print(f"      [{status}] {r['table']}")

    _report(errors)


def _report(errors):
    print(f"\n{'=' * 70}")
    if errors:
        print("RESULT: FAIL")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    else:
        print("RESULT: PASS — All assertions satisfied")
        sys.exit(0)


if __name__ == "__main__":
    main()
