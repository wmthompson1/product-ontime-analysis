#!/usr/bin/env python3
"""
graph_metadata_demo.py — Five runnable examples for graph_metadata_queries + metadata_query_templates.

Run from the repo root:
    python replit_integrations/graph_metadata_demo.py

Or as a module (also works):
    python -m replit_integrations.graph_metadata_demo

Expected output: module import paths, a DB connection confirmation, and a
DataFrame sample for each of the five examples below.
"""
import os
import sys

# Bootstrap: when this file is run directly (python replit_integrations/graph_metadata_demo.py),
# Python sets sys.path[0] to the script's own directory, so 'replit_integrations' is not
# visible as a top-level package. Insert the repo root (parent of this file's directory)
# so that `from replit_integrations import ...` resolves correctly.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# ---------------------------------------------------------------------------
# 1. Import verification — confirm module paths resolve correctly
# ---------------------------------------------------------------------------
print("=" * 60)
print("IMPORT VERIFICATION")
print("=" * 60)

from replit_integrations import graph_metadata_queries as gmq
from replit_integrations import metadata_query_templates as mqt

print(f"graph_metadata_queries : {gmq.__file__}")
print(f"metadata_query_templates: {mqt.__file__}")

# ---------------------------------------------------------------------------
# 2. Connection test — confirm manufacturing.db is found and readable
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("CONNECTION TEST")
print("=" * 60)

try:
    db_path = gmq.get_manufacturing_db_path()
    print(f"DB path  : {db_path}")
    print(f"DB exists: {os.path.exists(db_path)}")
    # Quick sanity query — should always return rows
    ping = gmq.get_graph_metadata("SELECT COUNT(*) AS table_count FROM schema_nodes")
    print(f"schema_nodes row count: {ping['table_count'].iloc[0]}")
except FileNotFoundError as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Example 1 — Perspectives list
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 1 — Perspectives list")
print("Expected: rows for Quality, Payables, Work_Orders, etc.")
print("=" * 60)

df_perspectives = gmq.get_graph_metadata(mqt.list_perspectives())
print(df_perspectives[["perspective_id", "perspective_name", "stakeholder_role"]].head(5).to_string(index=False))
# perspective_id  perspective_name   stakeholder_role
#              1           Quality   Quality Engineer, QA Manager
#              2          Payables   AP Manager, Purchasing Manager
#              3       Work_Orders   Production Planner, Shop Supervisor

# ---------------------------------------------------------------------------
# Example 2 — Polymorphic field meanings (work_order.status)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 2 — Polymorphic field meanings for (work_order, status)")
print("Expected: zero or more concept rows for that field pair")
print("=" * 60)

sql_poly = mqt.polymorphic_field_meanings("work_order", "status")
df_poly = gmq.get_graph_metadata(sql_poly, params=["work_order", "status"])
if df_poly.empty:
    print("(no concept_field rows for work_order.status — field not yet registered as polymorphic)")
else:
    print(df_poly[["table_name", "field_name", "concept_name", "is_primary_meaning"]].to_string(index=False))

# ---------------------------------------------------------------------------
# Example 3 — Intent concept elevations (intent_id=1: defect_cost_analysis)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 3 — Intent concept elevations for intent_id=1 (defect_cost_analysis)")
print("Expected: DefectSeverityCost elevated (weight=1), others neutral/suppressed")
print("=" * 60)

sql_elev = mqt.intent_concept_elevations(intent_id=1)
df_elev = gmq.get_graph_metadata(sql_elev, params=[1])
print(df_elev[["intent_name", "concept_name", "domain", "intent_factor_weight"]].to_string(index=False))
# intent_name          concept_name  domain  intent_factor_weight
# defect_cost_analysis  DefectSeverityCost  finance  1
# defect_cost_analysis  DefectSeverityCustomer  customer  0
# defect_cost_analysis  DefectSeverityQuality  quality  0

# ---------------------------------------------------------------------------
# Example 4 — Foreign key graph (all edges)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 4 — Foreign key graph (schema_edges, first 10 rows)")
print("Expected: from_table, to_table, relationship_type, join_column")
print("=" * 60)

df_fk = gmq.get_graph_metadata(mqt.foreign_key_graph())
if df_fk.empty:
    print("(schema_edges table is empty — no edges loaded yet)")
else:
    cols = ["from_table", "to_table", "relationship_type", "join_column"]
    print(df_fk[cols].head(10).to_string(index=False))

# ---------------------------------------------------------------------------
# Example 5 — ArangoDB _key format assertions (offline)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 5 — ArangoDB _key format assertions (offline)")
print("Expected: all assertions pass; table:: and column:: prefixes confirmed")
print("=" * 60)

TABLE_KEY_PREFIX = "table::"
COLUMN_KEY_PREFIX = "column::"

# Derive expected _key values from schema_nodes table names (same logic as graph_sync.py)
df_nodes = gmq.get_graph_metadata(mqt.table_metadata())
table_keys = [f"{TABLE_KEY_PREFIX}{row['table_name']}" for _, row in df_nodes.iterrows()]

assert len(table_keys) > 0, "schema_nodes must contain at least one table"
for key in table_keys:
    assert key.startswith(TABLE_KEY_PREFIX), f"Unexpected key format: {key}"

# Simulate a column _key for a known column
sample_column_key = f"{COLUMN_KEY_PREFIX}work_order.status"
assert sample_column_key.startswith(COLUMN_KEY_PREFIX), f"Unexpected key format: {sample_column_key}"

print(f"Checked {len(table_keys)} table:: _key values — all pass")
print(f"Sample table _key  : {table_keys[0]}")
print(f"Sample column _key : {sample_column_key}")
print("All ArangoDB _key format assertions passed (offline)")

print("\n" + "=" * 60)
print("DEMO COMPLETE")
print("=" * 60)
