"""
Dev Path Review Demo — Graph-sourced Information Schema
========================================================
Tests and develops the Semantic Graph tab by selecting a table
and pulling its information_schema from the ArangoDB graph.

Step 1: Single table — production_lines information schema
Step 2: Multi-table join — production_lines + FK dependents

Usage:
    python hf-space-inventory-sqlgen/dev_path_review_demo.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))
from solder_engine_extended import SolderEngineExtended

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
MANIFEST_PATH = os.path.join(SCHEMA_DIR, "ground_truth", "reviewer_manifest.json")


def print_info_schema_table(result):
    col_w = max(len(c.column_name) for c in result.columns)
    type_w = max(len(c.data_type) for c in result.columns)

    header = f"  {'column_name':<{col_w}}  {'data_type':<{type_w}}  PK     FK     references"
    print(header)
    print("  " + "-" * len(header.strip()))

    for c in result.columns:
        ref = ""
        if c.is_foreign_key and c.references_table:
            ref = f"{c.references_table}({c.references_column})"
        print(
            f"  {c.column_name:<{col_w}}  {c.data_type:<{type_w}}  "
            f"{'YES' if c.is_primary_key else '   '}    "
            f"{'YES' if c.is_foreign_key else '   '}    "
            f"{ref}"
        )


def step1_single_table(engine):
    print("=" * 70)
    print("STEP 1: Information Schema — production_lines (single table)")
    print("  Source: ArangoDB graph (not SQLite)")
    print("=" * 70)
    print()

    result = engine.get_information_schema("production_lines")

    print(f"  Table: {result.table_name}")
    print(f"  Columns: {len(result.columns)}")
    print(f"  Primary keys: {result.primary_keys}")
    print(f"  Foreign keys: {result.foreign_keys}")
    print(f"  Source: {result.source}")
    print()

    print_info_schema_table(result)

    print()
    print("  JSON (for Semantic Graph tab):")
    print(json.dumps(result.to_dicts(), indent=2))


def step2_multi_table_join(engine):
    print()
    print("=" * 70)
    print("STEP 2: Join Schema — production_lines + FK dependents")
    print("  Source: ArangoDB graph (not SQLite)")
    print("=" * 70)
    print()

    join_result = engine.get_join_schema("production_lines")

    print(f"  Tables in join: {len(join_result.tables)}")
    print(f"  Join edges: {len(join_result.join_edges)}")
    print()

    print("  Join Edges:")
    for edge in join_result.join_edges:
        direction = edge["direction"]
        if direction == "inbound":
            print(
                f"    {edge['from_table']}.{edge['from_column']}  "
                f"--FK-->  {edge['to_table']}.{edge['to_column']}  "
                f"(dependent references production_lines)"
            )
        else:
            print(
                f"    {edge['from_table']}.{edge['from_column']}  "
                f"--FK-->  {edge['to_table']}.{edge['to_column']}  "
                f"(production_lines references parent)"
            )

    for schema in join_result.tables:
        print()
        print(f"  --- {schema.table_name} ---")
        print_info_schema_table(schema)

    print()
    print("  Combined JSON (for Semantic Graph tab):")
    print(json.dumps(join_result.to_dicts(), indent=2)[:2000])
    if len(json.dumps(join_result.to_dicts(), indent=2)) > 2000:
        print("  ... (truncated for display)")

    print()
    print("  Join Edges JSON:")
    print(json.dumps(join_result.join_edges, indent=2))


def step3_solder_engine_unchanged(engine):
    print()
    print("=" * 70)
    print("STEP 3: Verify SolderEngine functions still work (no interference)")
    print("=" * 70)
    print()

    intents = engine.get_available_intents()
    print(f"  get_available_intents(): {len(intents)} intents")

    weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityCost")
    print(f"  get_elevation_weight('defect_cost_analysis', 'DefectSeverityCost'): {weight}")

    bindings = engine.load_approved_bindings()
    print(f"  load_approved_bindings(): {len(bindings)} bindings")

    binding = engine.find_binding_for_concept("DefectSeverityCost", "Finance")
    print(f"  find_binding_for_concept('DefectSeverityCost', 'Finance'): {binding.binding_key if binding else None}")

    result = engine.solder(
        intent_name="defect_cost_analysis",
        target_concept="DefectSeverityCost",
        target_dialect="sqlite"
    )
    print(f"  solder('defect_cost_analysis'): concept={result.concept}, weight={result.elevation_weight}")
    print(f"    SQL preview: {result.soldered_sql[:80]}...")

    passed = all([
        len(intents) > 0,
        weight == 1.0,
        len(bindings) > 0,
        binding is not None,
        result.concept == "DefectSeverityCost",
    ])
    print()
    print(f"  Interference check: {'PASS — all SolderEngine functions unaffected' if passed else 'FAIL'}")


def main():
    engine = SolderEngineExtended(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    tables = engine.get_available_tables()
    print(f"Available tables in graph: {len(tables)}")
    for t in tables:
        print(f"  - {t}")
    print()

    step1_single_table(engine)
    step2_multi_table_join(engine)
    step3_solder_engine_unchanged(engine)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
