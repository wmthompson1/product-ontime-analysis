"""
Unit test: Forward and Backward AQL traversal for atomic column nodes.

Run:  python Utilities/ArangoFixtures/test_atomic_traversal.py

Follow along in ArangoDB UI:
  Graph > manufacturing_graph > Start node: manufacturing_graph_node/production_lines.line_id
"""

import os
import sys

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
                target_column: v.column_name,
                perspective: e.perspective
            }
    )

    RETURN {
        source_table: col.table_name,
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

passed = 0
failed = 0


def assert_eq(label, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"    [PASS] {label}")
    else:
        failed += 1
        print(f"    [FAIL] {label}: expected {expected}, got {actual}")


def assert_true(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"    [PASS] {label}")
    else:
        failed += 1
        print(f"    [FAIL] {label}")


def forward(db, table_name):
    cursor = db.aql.execute(
        FORWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_table": table_name,
            "graph_name": GRAPH_NAME,
        },
    )
    return list(cursor)


def backward(db, target_key):
    cursor = db.aql.execute(
        BACKWARD_AQL,
        bind_vars={
            "@vertex_collection": VERTEX_COLLECTION,
            "target_key": target_key,
            "graph_name": GRAPH_NAME,
        },
    )
    return list(cursor)


def main():
    config = ArangoDBConfig()
    persistence = ArangoDBGraphPersistence(config)
    db = persistence._db

    print("=" * 60)
    print("TEST 1: Forward Projection — production_lines")
    print("  AQL: Filter table_name == 'production_lines'")
    print("  UI:  Graph tab > manufacturing_graph_node/table_production_lines")
    print("=" * 60)

    results = forward(db, "production_lines")

    assert_true("production_lines has columns", len(results) > 0)
    assert_eq("column count", len(results), 12)

    col_map = {r["source_column"]: r for r in results}
    expected_cols = ["line_id", "line_name", "facility_location", "line_type",
                     "theoretical_capacity", "actual_capacity", "efficiency_rating",
                     "installation_date", "last_maintenance_date", "status",
                     "supervisor", "created_at"]
    for col in expected_cols:
        assert_true(f"column '{col}' exists", col in col_map)

    assert_true("line_id is primary key", col_map.get("line_id", {}).get("is_primary_key", False))
    assert_eq("line_id is NOT a foreign key (it's the target)", col_map.get("line_id", {}).get("is_foreign_key"), False)

    print()
    print("  DDL Reconstruction:")
    for r in results:
        fk_str = ""
        if r["is_foreign_key"]:
            fk = r["foreign_key_details"]
            fk_str = f" REFERENCES {fk['target_table']}({fk['target_column']})"
        pk_str = " PRIMARY KEY" if r["is_primary_key"] else ""
        print(f"    {r['source_column']:20s} {r['data_type']}{pk_str}{fk_str}")

    print()
    print("=" * 60)
    print("TEST 2: Backward Trace — production_lines.line_id")
    print("  AQL: INBOUND from production_lines.line_id")
    print("  UI:  Graph tab > manufacturing_graph_node/production_lines.line_id")
    print("=" * 60)

    dependents = backward(db, "production_lines.line_id")

    assert_true("has inbound FK edges", len(dependents) > 0)
    assert_eq("dependent count", len(dependents), 1)

    dep_tables = {r["source_table"] for r in dependents}
    assert_true("downtime_events depends on line_id", "downtime_events" in dep_tables)

    print()
    print("  Impact Report:")
    for r in dependents:
        print(f"    {r['source_table']}.{r['source_column']} ({r['data_type']})  --FK-->  production_lines.line_id")

    print()
    print("=" * 60)
    print("TEST 3: Forward Projection — downtime_events (multi-FK table)")
    print("  AQL: Filter table_name == 'downtime_events'")
    print("=" * 60)

    results = forward(db, "downtime_events")

    assert_eq("downtime_events column count", len(results), 14)

    col_map = {r["source_column"]: r for r in results}

    assert_true("line_id is FK", col_map.get("line_id", {}).get("is_foreign_key", False))
    assert_eq("line_id FK target table", col_map.get("line_id", {}).get("foreign_key_details", {}).get("target_table"), "production_lines")
    assert_eq("line_id FK target column", col_map.get("line_id", {}).get("foreign_key_details", {}).get("target_column"), "line_id")

    assert_true("equipment_id is FK", col_map.get("equipment_id", {}).get("is_foreign_key", False))
    assert_eq("equipment_id FK target", col_map.get("equipment_id", {}).get("foreign_key_details", {}).get("target_table"), "equipment_metrics")

    assert_eq("event_id is NOT FK", col_map.get("event_id", {}).get("is_foreign_key"), False)

    print()
    print("  DDL Reconstruction:")
    for r in results:
        fk_str = ""
        if r["is_foreign_key"]:
            fk = r["foreign_key_details"]
            fk_str = f" REFERENCES {fk['target_table']}({fk['target_column']})"
        pk_str = " PRIMARY KEY" if r["is_primary_key"] else ""
        print(f"    {r['source_column']:30s} {r['data_type']}{pk_str}{fk_str}")

    print()
    print("=" * 60)
    print("TEST 4: Backward Trace — equipment_metrics.equipment_id (fan-in)")
    print("  AQL: INBOUND from equipment_metrics.equipment_id")
    print("=" * 60)

    dependents = backward(db, "equipment_metrics.equipment_id")

    assert_true("has multiple inbound FKs", len(dependents) >= 3)

    dep_tables = {r["source_table"] for r in dependents}
    assert_true("downtime_events depends", "downtime_events" in dep_tables)
    assert_true("equipment_reliability depends", "equipment_reliability" in dep_tables)
    assert_true("failure_events depends", "failure_events" in dep_tables)

    print()
    print("  Impact Report:")
    for r in dependents:
        print(f"    {r['source_table']}.{r['source_column']} ({r['data_type']})  --FK-->  equipment_metrics.equipment_id")

    print()
    print("=" * 60)
    total = passed + failed
    print(f"RESULT: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("ALL TESTS PASSED")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
