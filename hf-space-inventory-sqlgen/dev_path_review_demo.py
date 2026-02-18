"""
Dev Path Review Demo — Graph-sourced Information Schema
========================================================
Tests and develops the Semantic Graph tab by selecting a table
and pulling its information_schema from the ArangoDB graph.

Interactive mode: Select a table from the graph to inspect.
CLI mode: Pass a table name as argument.

Step 1: Single table — information schema from graph
Step 2: Multi-table join — base table + FK dependents/parents

Usage:
    python hf-space-inventory-sqlgen/dev_path_review_demo.py
    python hf-space-inventory-sqlgen/dev_path_review_demo.py production_lines
    python hf-space-inventory-sqlgen/dev_path_review_demo.py downtime_events
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
    if not result.columns:
        print("  (no columns)")
        return

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


def select_table(engine):
    tables = engine.get_available_tables()

    if len(sys.argv) > 1:
        selected = sys.argv[1]
        if selected in tables:
            return selected
        print(f"Table '{selected}' not found in graph.")
        print()

    print("=" * 70)
    print("Graph-sourced Datasets — Select a table")
    print("=" * 70)
    print()

    for i, t in enumerate(tables, 1):
        info = engine.get_information_schema(t)
        pk_str = ", ".join(info.primary_keys) if info.primary_keys else "-"
        fk_count = len(info.foreign_keys)
        fk_str = f"{fk_count} FK" if fk_count else "no FK"
        print(f"  [{i:2d}] {t:<30s}  {len(info.columns):2d} cols  PK={pk_str:<15s}  {fk_str}")

    print()
    while True:
        try:
            choice = input("Enter table number (or name): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(tables):
                    return tables[idx]
                print(f"  Out of range. Enter 1-{len(tables)}.")
            elif choice in tables:
                return choice
            else:
                print(f"  '{choice}' not found. Try again.")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)


def step1_single_table(engine, table_name):
    print()
    print("=" * 70)
    print(f"STEP 1: Information Schema — {table_name}")
    print("  Source: ArangoDB graph (Atomic AQL)")
    print("=" * 70)
    print()

    result = engine.get_information_schema(table_name)
    raw_nodes = engine.get_raw_graph_nodes(table_name)

    print(f"  Table: {result.table_name}")
    print(f"  Columns: {len(result.columns)}")
    print(f"  Primary keys: {result.primary_keys}")
    print(f"  Foreign keys: {result.foreign_keys}")
    print(f"  Source: {result.source}")
    print(f"  Raw graph nodes: {len(raw_nodes)} (exact match: {len(result.columns) == len(raw_nodes)})")
    print()

    print_info_schema_table(result)

    print()
    print("  JSON (for Semantic Graph tab):")
    json_str = json.dumps(result.to_dicts(), indent=2)
    if len(json_str) > 3000:
        print(json_str[:3000])
        print("  ... (truncated)")
    else:
        print(json_str)


def step2_multi_table_join(engine, table_name):
    print()
    print("=" * 70)
    print(f"STEP 2: Join Schema — {table_name} + FK relationships")
    print("  Source: ArangoDB graph (Atomic AQL)")
    print("=" * 70)
    print()

    join_result = engine.get_join_schema(table_name)

    print(f"  Tables in join: {len(join_result.tables)}")
    print(f"  Join edges: {len(join_result.join_edges)}")
    print()

    if join_result.join_edges:
        print("  Join Edges:")
        for edge in join_result.join_edges:
            direction = edge["direction"]
            if direction == "inbound":
                print(
                    f"    {edge['from_table']}.{edge['from_column']}  "
                    f"--FK-->  {edge['to_table']}.{edge['to_column']}  "
                    f"(dependent references {table_name})"
                )
            else:
                print(
                    f"    {edge['from_table']}.{edge['from_column']}  "
                    f"--FK-->  {edge['to_table']}.{edge['to_column']}  "
                    f"({table_name} references parent)"
                )
    else:
        print("  (no join edges — isolated table)")

    for schema in join_result.tables:
        print()
        print(f"  --- {schema.table_name} ---")
        print_info_schema_table(schema)

    print()
    print("  Join Edges JSON:")
    print(json.dumps(join_result.join_edges, indent=2))


def main():
    engine = SolderEngineExtended(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    table_name = select_table(engine)

    step1_single_table(engine, table_name)
    step2_multi_table_join(engine, table_name)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
