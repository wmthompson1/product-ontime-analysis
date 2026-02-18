"""
Demo: Forward Projection + Backward Trace AQL for Atomic Solder.

Runs the exact AQL queries used in test_atomic_traversal.py and prints
the raw results for architect review.

Usage:
    python Utilities/ArangoFixtures/demo_forward_backward_aql.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"

FORWARD_AQL = '''
FOR col IN @@vertex_collection
    FILTER col.table_name == @target_table
       AND col.node_type == "atomic_column"

    LET fk_solder = (
        FOR v, e IN 1..1 OUTBOUND col._id GRAPH @graph_name
            FILTER e.is_foreign_key == true
            RETURN {
                target_table: v.table_name,
                target_column: v.column_name
            }
    )

    RETURN {
        source_column: col.column_name,
        data_type: col.data_type,
        is_primary_key: col.is_primary_key,
        is_foreign_key: LENGTH(fk_solder) > 0,
        foreign_key_details: fk_solder[0]
    }
'''

BACKWARD_AQL = '''
FOR col_target IN @@vertex_collection
    FILTER col_target._key == @target_key

    FOR v, e IN 1..1 INBOUND col_target._id GRAPH @graph_name
        FILTER e.is_foreign_key == true
        RETURN {
            source_table: v.table_name,
            source_column: v.column_name,
            data_type: v.data_type
        }
'''


def run_forward(db, table_name):
    return list(db.aql.execute(
        FORWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_table": table_name,
            "graph_name": GRAPH_NAME,
        },
    ))


def run_backward(db, target_key):
    return list(db.aql.execute(
        BACKWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_key": target_key,
            "graph_name": GRAPH_NAME,
        },
    ))


def render_ddl(table_name, rows):
    lines = []
    for r in rows:
        parts = [f"    {r['source_column']} {r['data_type']}"]
        if r["is_primary_key"]:
            parts.append("NOT NULL PRIMARY KEY")
        if r["is_foreign_key"]:
            fk = r["foreign_key_details"]
            parts.append(f"REFERENCES {fk['target_table']}({fk['target_column']})")
        lines.append(" ".join(parts))
    return f"CREATE TABLE {table_name} (\n" + ",\n".join(lines) + "\n);"


def main():
    config = ArangoDBConfig()
    persistence = ArangoDBGraphPersistence(config)
    db = persistence._db

    print("=" * 64)
    print("QUERY 1: Forward Projection — production_lines")
    print("=" * 64)
    print()
    print("AQL:")
    print(FORWARD_AQL.replace("@@vertex_collection", VERTEX_COLLECTION)
                     .replace("@target_table", '"production_lines"')
                     .replace("@graph_name", f'"{GRAPH_NAME}"'))
    print()

    rows = run_forward(db, "production_lines")
    print(f"Result: {len(rows)} columns")
    print()
    print("JSON:")
    print(json.dumps(rows, indent=2))
    print()
    print("DDL Reconstruction:")
    print(render_ddl("production_lines", rows))

    print()
    print("=" * 64)
    print("QUERY 2: Backward Trace — production_lines.line_id")
    print("=" * 64)
    print()
    print("AQL:")
    print(BACKWARD_AQL.replace("@@vertex_collection", VERTEX_COLLECTION)
                      .replace("@target_key", '"production_lines.line_id"')
                      .replace("@graph_name", f'"{GRAPH_NAME}"'))
    print()

    deps = run_backward(db, "production_lines.line_id")
    print(f"Result: {len(deps)} dependents")
    print()
    print("JSON:")
    print(json.dumps(deps, indent=2))
    print()
    print("Impact:")
    for d in deps:
        print(f"  {d['source_table']}.{d['source_column']} ({d['data_type']})  --FK-->  production_lines.line_id")

    print()
    print("=" * 64)
    print("DONE")
    print("=" * 64)


if __name__ == "__main__":
    main()
