"""
Solder Extended Validation Test Suite
=======================================
Tests the SolderEngineExtended's graph-sourced information_schema
using ONLY the ArangoDB manufacturing graph.

Step 1: Single table — assert columns/types match raw graph nodes exactly
Step 2: Multi-table join — assert join keys match raw graph edges exactly

All assertions validate get_information_schema output against raw AQL
node/edge data to prove the Atomic AQL is correctly wrapped.

Run: python hf-space-inventory-sqlgen/test_solder_validation_extended.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from solder_engine_extended import SolderEngineExtended

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
MANIFEST_PATH = os.path.join(SCHEMA_DIR, "ground_truth", "reviewer_manifest.json")


def make_engine():
    return SolderEngineExtended(db_path=DB_PATH, manifest_path=MANIFEST_PATH)


def test_available_tables():
    engine = make_engine()
    tables = engine.get_available_tables()
    assert len(tables) > 0, "Expected at least one table in graph"
    assert "production_lines" in tables
    assert "downtime_events" in tables
    assert "equipment_metrics" in tables
    assert "suppliers" in tables
    print(f"PASS: {len(tables)} tables available in graph")


def test_step1_columns_match_raw_nodes():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")
    raw_nodes = engine.get_raw_graph_nodes("production_lines")

    assert len(result.columns) == len(raw_nodes), \
        f"Column count mismatch: info_schema={len(result.columns)}, raw={len(raw_nodes)}"

    info_by_col = {c.column_name: c for c in result.columns}
    raw_by_col = {r["column_name"]: r for r in raw_nodes}

    assert set(info_by_col.keys()) == set(raw_by_col.keys()), \
        f"Column name sets differ: {set(info_by_col.keys()) ^ set(raw_by_col.keys())}"

    for col_name in sorted(raw_by_col.keys()):
        raw = raw_by_col[col_name]
        info = info_by_col[col_name]

        assert info.table_name == raw["table_name"], \
            f"{col_name}: table_name mismatch ({info.table_name} vs {raw['table_name']})"
        assert info.data_type == raw["data_type"], \
            f"{col_name}: data_type mismatch ({info.data_type} vs {raw['data_type']})"
        assert info.is_primary_key == raw["is_primary_key"], \
            f"{col_name}: is_primary_key mismatch ({info.is_primary_key} vs {raw['is_primary_key']})"
        assert info.is_foreign_key == raw["is_foreign_key"], \
            f"{col_name}: is_foreign_key mismatch ({info.is_foreign_key} vs {raw['is_foreign_key']})"
        assert info.references_table == raw.get("references_table"), \
            f"{col_name}: references_table mismatch ({info.references_table} vs {raw.get('references_table')})"
        assert info.references_column == raw.get("references_column"), \
            f"{col_name}: references_column mismatch ({info.references_column} vs {raw.get('references_column')})"

    print(f"PASS: production_lines — {len(result.columns)} columns match raw graph nodes exactly")


def test_step1_types_match_raw_nodes():
    engine = make_engine()

    for table in ["production_lines", "downtime_events", "equipment_metrics", "suppliers"]:
        result = engine.get_information_schema(table)
        raw_nodes = engine.get_raw_graph_nodes(table)

        raw_types = {r["column_name"]: r["data_type"] for r in raw_nodes}
        info_types = {c.column_name: c.data_type for c in result.columns}

        assert info_types == raw_types, \
            f"{table}: type map mismatch\n  info: {info_types}\n  raw:  {raw_types}"

    print("PASS: Column types match raw graph nodes across 4 tables")


def test_step1_pk_flags_match_raw_nodes():
    engine = make_engine()

    for table in ["production_lines", "downtime_events", "equipment_metrics"]:
        result = engine.get_information_schema(table)
        raw_nodes = engine.get_raw_graph_nodes(table)

        raw_pks = {r["column_name"]: r["is_primary_key"] for r in raw_nodes}
        info_pks = {c.column_name: c.is_primary_key for c in result.columns}

        assert info_pks == raw_pks, \
            f"{table}: PK flags mismatch\n  info: {info_pks}\n  raw:  {raw_pks}"

    print("PASS: PK flags match raw graph nodes across 3 tables")


def test_step1_fk_flags_match_raw_nodes():
    engine = make_engine()

    for table in ["production_lines", "downtime_events", "equipment_metrics"]:
        result = engine.get_information_schema(table)
        raw_nodes = engine.get_raw_graph_nodes(table)

        raw_fks = {r["column_name"]: r["is_foreign_key"] for r in raw_nodes}
        info_fks = {c.column_name: c.is_foreign_key for c in result.columns}

        assert info_fks == raw_fks, \
            f"{table}: FK flags mismatch\n  info: {info_fks}\n  raw:  {raw_fks}"

        for r in raw_nodes:
            if r["is_foreign_key"]:
                col = [c for c in result.columns if c.column_name == r["column_name"]][0]
                assert col.references_table == r["references_table"], \
                    f"{table}.{r['column_name']}: references_table mismatch"
                assert col.references_column == r["references_column"], \
                    f"{table}.{r['column_name']}: references_column mismatch"

    print("PASS: FK flags and references match raw graph nodes across 3 tables")


def test_step1_json_matches_raw_nodes():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")
    raw_nodes = engine.get_raw_graph_nodes("production_lines")

    info_dicts = result.to_dicts()
    info_by_col = {d["column_name"]: d for d in info_dicts}
    raw_by_col = {r["column_name"]: r for r in raw_nodes}

    for col_name in sorted(raw_by_col.keys()):
        raw = raw_by_col[col_name]
        info = info_by_col[col_name]

        for key in ["table_name", "column_name", "data_type",
                     "is_primary_key", "is_foreign_key",
                     "references_table", "references_column"]:
            assert info[key] == raw.get(key), \
                f"{col_name}.{key}: JSON mismatch ({info[key]} vs {raw.get(key)})"

    print("PASS: JSON output matches raw graph nodes field-for-field")


def test_step2_join_keys_match_raw_edges():
    engine = make_engine()
    join_result = engine.get_join_schema("production_lines")

    raw_deps = engine.get_raw_graph_edges("production_lines", "line_id")
    raw_dep_tables = {r["table_name"] for r in raw_deps}

    join_dep_tables = {
        e["from_table"] for e in join_result.join_edges
        if e["direction"] == "inbound"
    }

    assert join_dep_tables == raw_dep_tables, \
        f"Inbound dependents mismatch:\n  join_schema: {join_dep_tables}\n  raw_edges:   {raw_dep_tables}"

    for dep_table in raw_dep_tables:
        dep_info = engine.get_information_schema(dep_table)
        dep_raw = engine.get_raw_graph_nodes(dep_table)

        dep_fk_cols = {r["column_name"] for r in dep_raw if r["is_foreign_key"]
                       and r.get("references_table") == "production_lines"}

        join_fk_cols = {
            e["from_column"] for e in join_result.join_edges
            if e["from_table"] == dep_table and e["to_table"] == "production_lines"
        }

        assert join_fk_cols == dep_fk_cols, \
            f"{dep_table} FK columns mismatch:\n  join: {join_fk_cols}\n  raw:  {dep_fk_cols}"

    print(f"PASS: Join keys match raw graph edges — {len(raw_dep_tables)} dependents verified")


def test_step2_join_keys_match_raw_edges_fan_in():
    engine = make_engine()
    join_result = engine.get_join_schema("equipment_metrics")

    raw_deps = engine.get_raw_graph_edges("equipment_metrics", "equipment_id")
    raw_dep_tables = {r["table_name"] for r in raw_deps}

    join_dep_tables = {
        e["from_table"] for e in join_result.join_edges
        if e["direction"] == "inbound"
    }

    assert join_dep_tables == raw_dep_tables, \
        f"Fan-in dependents mismatch:\n  join_schema: {join_dep_tables}\n  raw_edges:   {raw_dep_tables}"

    for dep_table in raw_dep_tables:
        dep_raw = engine.get_raw_graph_nodes(dep_table)
        dep_fk_refs = {
            (r["column_name"], r["references_table"], r["references_column"])
            for r in dep_raw
            if r["is_foreign_key"] and r.get("references_table") == "equipment_metrics"
        }

        join_fk_refs = {
            (e["from_column"], e["to_table"], e["to_column"])
            for e in join_result.join_edges
            if e["from_table"] == dep_table and e["to_table"] == "equipment_metrics"
        }

        assert join_fk_refs == dep_fk_refs, \
            f"{dep_table} FK refs mismatch:\n  join: {join_fk_refs}\n  raw:  {dep_fk_refs}"

    print(f"PASS: Fan-in join keys match raw edges — {len(raw_dep_tables)} dependents verified")


def test_step2_outbound_join_keys_match_raw_nodes():
    engine = make_engine()
    join_result = engine.get_join_schema("downtime_events")

    raw_nodes = engine.get_raw_graph_nodes("downtime_events")
    raw_fk_refs = {
        (r["column_name"], r["references_table"], r["references_column"])
        for r in raw_nodes
        if r["is_foreign_key"]
    }

    join_outbound_refs = {
        (e["from_column"], e["to_table"], e["to_column"])
        for e in join_result.join_edges
        if e["direction"] == "outbound"
    }

    assert join_outbound_refs == raw_fk_refs, \
        f"Outbound FK refs mismatch:\n  join: {join_outbound_refs}\n  raw:  {raw_fk_refs}"

    print(f"PASS: Outbound join keys match raw FK nodes — {len(raw_fk_refs)} FKs verified")


def test_step2_join_schema_tables_have_matching_schemas():
    engine = make_engine()
    join_result = engine.get_join_schema("production_lines")

    for schema in join_result.tables:
        raw_nodes = engine.get_raw_graph_nodes(schema.table_name)
        info_types = {c.column_name: c.data_type for c in schema.columns}
        raw_types = {r["column_name"]: r["data_type"] for r in raw_nodes}

        assert info_types == raw_types, \
            f"{schema.table_name}: join schema types != raw graph types"

    print(f"PASS: All {len(join_result.tables)} tables in join schema match raw graph exactly")


if __name__ == "__main__":
    print("=" * 60)
    print("SOLDER EXTENDED VALIDATION — GRAPH ONLY")
    print("  Assert info_schema output == raw graph nodes exactly")
    print("=" * 60)

    tests = [
        ("Available Tables (graph)", test_available_tables),
        ("Step 1: Columns match raw nodes", test_step1_columns_match_raw_nodes),
        ("Step 1: Types match raw nodes (4 tables)", test_step1_types_match_raw_nodes),
        ("Step 1: PK flags match raw nodes", test_step1_pk_flags_match_raw_nodes),
        ("Step 1: FK flags match raw nodes", test_step1_fk_flags_match_raw_nodes),
        ("Step 1: JSON matches raw nodes", test_step1_json_matches_raw_nodes),
        ("Step 2: Join keys match raw edges", test_step2_join_keys_match_raw_edges),
        ("Step 2: Fan-in join keys match raw edges", test_step2_join_keys_match_raw_edges_fan_in),
        ("Step 2: Outbound join keys match raw nodes", test_step2_outbound_join_keys_match_raw_nodes),
        ("Step 2: Join table schemas match raw graph", test_step2_join_schema_tables_have_matching_schemas),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)
