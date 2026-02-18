"""
Solder Extended Validation Test Suite
=======================================
Tests the SolderEngineExtended's graph-sourced information_schema
against the same patterns used in test_solder_validation.py.

Step 1: Single table — production_lines information schema from graph
Step 2: Multi-table join — production_lines + FK dependents
Step 3: Verify SolderEngine parent functions are unaffected

Run: python hf-space-inventory-sqlgen/test_solder_extended_validation.py
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
    assert "production_lines" in tables, "production_lines missing from graph"
    assert "downtime_events" in tables, "downtime_events missing from graph"
    print(f"PASS: {len(tables)} tables available in graph")


def test_single_table_info_schema():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")

    assert result.table_name == "production_lines"
    assert result.source == "arangodb_graph"
    assert len(result.columns) == 12, f"Expected 12 columns, got {len(result.columns)}"

    col_names = [c.column_name for c in result.columns]
    assert "line_id" in col_names, "line_id missing"
    assert "line_name" in col_names, "line_name missing"
    assert "facility_location" in col_names, "facility_location missing"
    assert "status" in col_names, "status missing"

    assert result.primary_keys == ["line_id"], f"Expected PK ['line_id'], got {result.primary_keys}"
    assert result.foreign_keys == [], f"Expected no FKs, got {result.foreign_keys}"

    print(f"PASS: production_lines — {len(result.columns)} columns, PK={result.primary_keys}")


def test_single_table_column_types():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")
    type_map = {c.column_name: c.data_type for c in result.columns}

    assert type_map["line_id"] == "INTEGER"
    assert type_map["line_name"] == "TEXT"
    assert type_map["efficiency_rating"] == "REAL"
    assert type_map["installation_date"] == "DATE"
    assert type_map["created_at"] == "DATETIME"

    print("PASS: Column data types match expected values")


def test_single_table_pk_flags():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")
    pk_flags = {c.column_name: c.is_primary_key for c in result.columns}

    assert pk_flags["line_id"] is True, "line_id should be PK"
    for col in ["line_name", "facility_location", "status", "supervisor"]:
        assert pk_flags[col] is False, f"{col} should not be PK"

    print("PASS: Primary key flags correct")


def test_single_table_fk_flags():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")

    for c in result.columns:
        assert c.is_foreign_key is False, f"{c.column_name} should not be FK on production_lines"
        assert c.references_table is None, f"{c.column_name} should have no FK reference"
        assert c.references_column is None, f"{c.column_name} should have no FK reference column"

    print("PASS: No foreign keys on production_lines (leaf table)")


def test_single_table_json_output():
    engine = make_engine()
    result = engine.get_information_schema("production_lines")
    dicts = result.to_dicts()

    assert len(dicts) == 12
    for d in dicts:
        assert "table_name" in d
        assert "column_name" in d
        assert "data_type" in d
        assert "is_primary_key" in d
        assert "is_foreign_key" in d
        assert "references_table" in d
        assert "references_column" in d
        assert d["table_name"] == "production_lines"

    print("PASS: JSON output has all required keys")


def test_multi_fk_table_info_schema():
    engine = make_engine()
    result = engine.get_information_schema("downtime_events")

    assert len(result.columns) == 14, f"Expected 14 columns, got {len(result.columns)}"
    assert result.primary_keys == ["event_id"]

    fks = result.foreign_keys
    fk_cols = {fk["column"] for fk in fks}
    assert "line_id" in fk_cols, "line_id should be FK"
    assert "equipment_id" in fk_cols, "equipment_id should be FK"

    line_fk = [fk for fk in fks if fk["column"] == "line_id"][0]
    assert line_fk["references_table"] == "production_lines"
    assert line_fk["references_column"] == "line_id"

    equip_fk = [fk for fk in fks if fk["column"] == "equipment_id"][0]
    assert equip_fk["references_table"] == "equipment_metrics"
    assert equip_fk["references_column"] == "equipment_id"

    print(f"PASS: downtime_events — {len(fks)} FKs: {fk_cols}")


def test_join_schema_discovery():
    engine = make_engine()
    join_result = engine.get_join_schema("production_lines")

    table_names = [t.table_name for t in join_result.tables]
    assert "production_lines" in table_names, "Base table missing from join schema"
    assert "downtime_events" in table_names, "downtime_events should be discovered via FK"

    assert len(join_result.join_edges) >= 1, "Expected at least 1 join edge"

    inbound_edges = [e for e in join_result.join_edges if e["direction"] == "inbound"]
    assert len(inbound_edges) >= 1, "Expected at least 1 inbound FK edge"

    dt_edge = [e for e in inbound_edges
               if e["from_table"] == "downtime_events" and e["from_column"] == "line_id"]
    assert len(dt_edge) == 1, "Expected downtime_events.line_id → production_lines.line_id edge"
    assert dt_edge[0]["to_table"] == "production_lines"
    assert dt_edge[0]["to_column"] == "line_id"

    print(f"PASS: Join schema — {len(join_result.tables)} tables, {len(join_result.join_edges)} edges")


def test_join_schema_combined_json():
    engine = make_engine()
    join_result = engine.get_join_schema("production_lines")
    dicts = join_result.to_dicts()

    tables_in_json = set(d["table_name"] for d in dicts)
    assert "production_lines" in tables_in_json
    assert "downtime_events" in tables_in_json

    for d in dicts:
        assert "table_name" in d
        assert "column_name" in d
        assert "data_type" in d
        assert "is_primary_key" in d
        assert "is_foreign_key" in d

    print(f"PASS: Combined JSON — {len(dicts)} rows across {len(tables_in_json)} tables")


def test_join_schema_fan_in():
    engine = make_engine()
    join_result = engine.get_join_schema("equipment_metrics")

    table_names = [t.table_name for t in join_result.tables]
    assert "equipment_metrics" in table_names

    dep_tables = {e["from_table"] for e in join_result.join_edges if e["direction"] == "inbound"}
    assert "downtime_events" in dep_tables, "downtime_events should reference equipment_metrics"
    assert "equipment_reliability" in dep_tables, "equipment_reliability should reference equipment_metrics"
    assert "failure_events" in dep_tables, "failure_events should reference equipment_metrics"

    print(f"PASS: Fan-in — equipment_metrics has {len(dep_tables)} dependents: {dep_tables}")


def test_parent_elevation_weight():
    engine = make_engine()
    weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityCost")
    assert weight == 1.0, f"Expected 1.0, got {weight}"
    print("PASS: Parent get_elevation_weight() unaffected")


def test_parent_load_bindings():
    engine = make_engine()
    bindings = engine.load_approved_bindings()
    assert len(bindings) > 0, "Expected at least one binding"
    print(f"PASS: Parent load_approved_bindings() — {len(bindings)} bindings")


def test_parent_find_binding():
    engine = make_engine()
    binding = engine.find_binding_for_concept("DefectSeverityCost", "Finance")
    assert binding is not None, "Expected binding for DefectSeverityCost"
    assert binding.concept_anchor == "DEFECTSEVERITYCOST"
    print(f"PASS: Parent find_binding_for_concept() — {binding.binding_key}")


def test_parent_solder():
    engine = make_engine()
    result = engine.solder(
        intent_name="defect_cost_analysis",
        target_concept="DefectSeverityCost",
        target_dialect="sqlite"
    )
    assert result.concept == "DefectSeverityCost"
    assert result.elevation_weight == 1.0
    assert "ncm_cost" in result.soldered_sql.lower()
    print(f"PASS: Parent solder() — concept={result.concept}, weight={result.elevation_weight}")


def test_parent_available_intents():
    engine = make_engine()
    intents = engine.get_available_intents()
    assert len(intents) > 0, "Expected at least one intent"
    print(f"PASS: Parent get_available_intents() — {len(intents)} intents")


if __name__ == "__main__":
    print("=" * 60)
    print("SOLDER EXTENDED VALIDATION TEST SUITE")
    print("=" * 60)

    tests = [
        ("Available Tables", test_available_tables),
        ("Single Table: Info Schema", test_single_table_info_schema),
        ("Single Table: Column Types", test_single_table_column_types),
        ("Single Table: PK Flags", test_single_table_pk_flags),
        ("Single Table: FK Flags", test_single_table_fk_flags),
        ("Single Table: JSON Output", test_single_table_json_output),
        ("Multi-FK Table: downtime_events", test_multi_fk_table_info_schema),
        ("Join Schema: Discovery", test_join_schema_discovery),
        ("Join Schema: Combined JSON", test_join_schema_combined_json),
        ("Join Schema: Fan-In (equipment_metrics)", test_join_schema_fan_in),
        ("Parent: Elevation Weight", test_parent_elevation_weight),
        ("Parent: Load Bindings", test_parent_load_bindings),
        ("Parent: Find Binding", test_parent_find_binding),
        ("Parent: Solder", test_parent_solder),
        ("Parent: Available Intents", test_parent_available_intents),
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
