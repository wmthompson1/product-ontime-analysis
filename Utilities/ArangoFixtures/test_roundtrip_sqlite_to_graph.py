"""
Round-trip validation: SQLite DDL  -->  ArangoDB Graph  -->  DDL Reconstruction.

Reads the SAME source data that load_atomic_nodes.py used to populate the graph,
then queries the graph and asserts every column and FK matches the original.

This proves:  DDL in  ==  DDL out  (the graph is a faithful digital twin).

Usage:
    python Utilities/ArangoFixtures/test_roundtrip_sqlite_to_graph.py
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db"
)

SKIP_TABLES = {
    "sqlite_sequence", "users",
    "schema_concepts", "schema_concept_fields",
    "schema_intents", "schema_intent_concepts",
    "schema_intent_queries", "schema_perspectives",
    "schema_intent_perspectives", "schema_perspective_concepts",
    "manufacturing_acronyms",
}

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"

FORWARD_AQL = '''
FOR col IN @@vertex_collection
    FILTER col.table_name == @target_table
       AND col.node_type == "atomic_column"
    LET fk_solder = (
        FOR v, e IN 1..1 OUTBOUND col._id GRAPH @graph_name
            FILTER e.is_foreign_key == true
            RETURN { target_table: v.table_name, target_column: v.column_name }
    )
    RETURN {
        column_name: col.column_name,
        data_type: col.data_type,
        is_primary_key: col.is_primary_key,
        is_foreign_key: LENGTH(fk_solder) > 0,
        fk_target_table: fk_solder[0].target_table,
        fk_target_column: fk_solder[0].target_column
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


def read_sqlite_schema(conn):
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if r[0] not in SKIP_TABLES
    ]

    schema = {}
    for table in sorted(tables):
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        fks = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()

        fk_map = {}
        for fk in fks:
            ref_table = fk[2]
            from_col = fk[3]
            to_col = fk[4]
            if ref_table not in SKIP_TABLES:
                fk_map[from_col] = (ref_table, to_col)

        columns = {}
        for col in cols:
            col_name = col[1]
            col_type = col[2] or "TEXT"
            is_pk = bool(col[5])
            fk_info = fk_map.get(col_name)
            columns[col_name] = {
                "data_type": col_type,
                "is_primary_key": is_pk,
                "is_foreign_key": fk_info is not None,
                "fk_target_table": fk_info[0] if fk_info else None,
                "fk_target_column": fk_info[1] if fk_info else None,
            }
        schema[table] = columns
    return schema


def query_graph_forward(db, table_name):
    rows = list(db.aql.execute(
        FORWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_table": table_name,
            "graph_name": GRAPH_NAME,
        },
    ))
    return {r["column_name"]: r for r in rows}


def query_graph_backward(db, target_key):
    return list(db.aql.execute(
        BACKWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_key": target_key,
            "graph_name": GRAPH_NAME,
        },
    ))


def main():
    conn = sqlite3.connect(SQLITE_PATH)
    sqlite_schema = read_sqlite_schema(conn)
    conn.close()

    config = ArangoDBConfig()
    persistence = ArangoDBGraphPersistence(config)
    db = persistence._db

    passed = 0
    failed = 0
    total_tables = len(sqlite_schema)

    def check(label, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
        else:
            failed += 1
            print(f"    [FAIL] {label}")

    print("=" * 70)
    print(f"FORWARD Round-Trip: {total_tables} tables from SQLite vs ArangoDB")
    print("=" * 70)

    for table_name, sqlite_cols in sorted(sqlite_schema.items()):
        graph_cols = query_graph_forward(db, table_name)

        check(f"{table_name}: column count ({len(sqlite_cols)} expected, {len(graph_cols)} got)",
              len(sqlite_cols) == len(graph_cols))

        for col_name, expected in sqlite_cols.items():
            if col_name not in graph_cols:
                check(f"{table_name}.{col_name}: missing in graph", False)
                continue

            actual = graph_cols[col_name]
            check(f"{table_name}.{col_name}: data_type ({expected['data_type']})",
                  actual["data_type"] == expected["data_type"])
            check(f"{table_name}.{col_name}: is_primary_key",
                  actual["is_primary_key"] == expected["is_primary_key"])
            check(f"{table_name}.{col_name}: is_foreign_key",
                  actual["is_foreign_key"] == expected["is_foreign_key"])

            if expected["is_foreign_key"]:
                check(f"{table_name}.{col_name}: FK target table",
                      actual["fk_target_table"] == expected["fk_target_table"])
                check(f"{table_name}.{col_name}: FK target column",
                      actual["fk_target_column"] == expected["fk_target_column"])

    print()
    print("=" * 70)
    print("BACKWARD Round-Trip: FK dependents from SQLite vs ArangoDB")
    print("=" * 70)

    pk_columns = {}
    for table_name, cols in sqlite_schema.items():
        for col_name, info in cols.items():
            if info["is_primary_key"]:
                pk_columns[f"{table_name}.{col_name}"] = table_name

    expected_backward = {}
    for table_name, cols in sqlite_schema.items():
        for col_name, info in cols.items():
            if info["is_foreign_key"]:
                target_key = f"{info['fk_target_table']}.{info['fk_target_column']}"
                expected_backward.setdefault(target_key, set()).add(
                    f"{table_name}.{col_name}"
                )

    for target_key in sorted(expected_backward.keys()):
        expected_deps = expected_backward[target_key]
        graph_deps = query_graph_backward(db, target_key)
        actual_deps = {f"{d['source_table']}.{d['source_column']}" for d in graph_deps}

        check(f"Backward {target_key}: dependent count ({len(expected_deps)} expected, {len(actual_deps)} got)",
              len(expected_deps) == len(actual_deps))

        for dep in expected_deps:
            check(f"Backward {target_key}: has dependent {dep}",
                  dep in actual_deps)

    for target_key, table_name in sorted(pk_columns.items()):
        if target_key not in expected_backward:
            graph_deps = query_graph_backward(db, target_key)
            check(f"Backward {target_key}: zero dependents (leaf PK)",
                  len(graph_deps) == 0)

    print()
    print("=" * 70)
    total = passed + failed
    print(f"RESULT: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("ALL TESTS PASSED — DDL in == DDL out")
    else:
        print("FAILURES DETECTED")
    print("=" * 70)


if __name__ == "__main__":
    main()
