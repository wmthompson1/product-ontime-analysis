#!/usr/bin/env python3
"""
graph_metadata_demo.py — Four runnable examples for graph_metadata_queries + metadata_query_templates.

Run from the repo root:
    python replit_integrations/graph_metadata_demo.py

Or as a module (also works):
    python -m replit_integrations.graph_metadata_demo

Expected output: module import paths, a DB connection confirmation, DataFrame
samples for the query examples, and offline composite-key parsing assertions.
"""
import os
import sqlite3
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
# Example 3 — Foreign key graph (all edges)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 3 — Foreign key graph (schema_edges, first 10 rows)")
print("Expected: from_table, to_table, relationship_type, join_column")
print("=" * 60)

df_fk = gmq.get_graph_metadata(mqt.foreign_key_graph())
if df_fk.empty:
    print("(schema_edges table is empty — no edges loaded yet)")
else:
    cols = ["from_table", "to_table", "relationship_type", "join_column"]
    print(df_fk[cols].head(10).to_string(index=False))

# ---------------------------------------------------------------------------
# Example 4 — Composite key slot-length structural parsing (offline)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EXAMPLE 4 — Composite key slot-length structural parsing (offline)")
print("Expected: every table/column/edge key classifies by slot count alone")
print("=" * 60)

# Composite key scheme (intent + UniqueID deferred — not bound to the physical
# schema footprint). Components are ':'-delimited, broad-first, and the
# perspective is always the terminal slot:
#     table vertex          table:family:perspective          (3 slots)
#     column vertex         table:column:family:perspective   (4 slots, perspective == 'system')
#     core structural edge  table:column:family:perspective   (4 slots, perspective == a business view)
#
# Parsing is therefore unambiguous from slot count + the terminal perspective
# token ALONE — no prefix tag needed. Constraint: 'system' is reserved for the
# structural layer, so a business view may never be named 'system'.
FAMILY_STRUCTURAL = "structural"
FAMILY_SEMANTIC = "semantic"
PERSPECTIVE_SYSTEM = "system"
SAMPLE_BUSINESS_VIEW = "payable"
# Canonical semantic-layer example (6 slots) — kept in lockstep with the
# key_scheme block embedded in graph_metadata.json (DEFERRED layer).
SAMPLE_SEMANTIC_KEY = "PAYABLE:INVOICE_ID:semantic:payable:elevates:PAY_ELE_PAY_INV_001"

KIND_TABLE = "table_vertex"
KIND_COLUMN = "column_vertex"
KIND_EDGE = "core_structural_edge"
KIND_SEMANTIC = "semantic_edge"


def _reject_delimiter(*parts):
    for p in parts:
        assert ":" not in str(p), f"component {p!r} must not contain the ':' delimiter"


def table_vertex_key(table):
    _reject_delimiter(table)
    return f"{table}:{FAMILY_STRUCTURAL}:{PERSPECTIVE_SYSTEM}"


def column_vertex_key(table, column):
    _reject_delimiter(table, column)
    return f"{table}:{column}:{FAMILY_STRUCTURAL}:{PERSPECTIVE_SYSTEM}"


def structural_edge_key(table, column, business_view):
    _reject_delimiter(table, column, business_view)
    return f"{table}:{column}:{FAMILY_STRUCTURAL}:{business_view}"


def classify_key(key):
    """Classify a composite key by slot count + terminal/family tokens.

    Slot layouts (family is slot index 2, perspective the terminal slot for the
    structural layer):
        3 slots                       -> table vertex
        4 slots, perspective 'system' -> column vertex
        4 slots, perspective business -> core structural edge
        6 slots, family 'semantic'    -> semantic edge
    """
    tokens = key.split(":")
    n = len(tokens)
    if n == 3:
        return KIND_TABLE
    if n == 4:
        return KIND_COLUMN if tokens[-1] == PERSPECTIVE_SYSTEM else KIND_EDGE
    if n == 6 and tokens[2] == FAMILY_SEMANTIC:
        return KIND_SEMANTIC
    raise ValueError(f"Unparseable key (slots={n}): {key!r}")


_db_path = gmq.get_manufacturing_db_path()
_conn = sqlite3.connect(_db_path)
_conn.row_factory = sqlite3.Row
n_tables = n_columns = n_edges = 0
sample_table_key = sample_column_key = sample_edge_key = None
try:
    _tables = [
        r["table_name"]
        for r in _conn.execute(
            "SELECT table_name FROM schema_nodes "
            "WHERE table_type = 'Table' ORDER BY table_name"
        )
    ]
    assert _tables, "schema_nodes must contain at least one table"

    for _t in _tables:
        # Table vertex — 3 slots, classifies as KIND_TABLE
        _tk = table_vertex_key(_t)
        assert _tk.count(":") == 2, f"table vertex must have 3 slots: {_tk!r}"
        assert classify_key(_tk) == KIND_TABLE, f"misclassified table vertex: {_tk!r}"
        n_tables += 1
        sample_table_key = sample_table_key or _tk

        _quoted = '"' + _t.replace('"', '""') + '"'
        try:
            _cols = [c["name"] for c in _conn.execute(f"PRAGMA table_info({_quoted})")]
        except sqlite3.Error:
            _cols = []

        for _c in _cols:
            # Column vertex — 4 slots, perspective 'system', classifies as KIND_COLUMN
            _ck = column_vertex_key(_t, _c)
            assert _ck.count(":") == 3, f"column vertex must have 4 slots: {_ck!r}"
            assert classify_key(_ck) == KIND_COLUMN, f"misclassified column vertex: {_ck!r}"
            n_columns += 1
            sample_column_key = sample_column_key or _ck

            # Core structural edge — 4 slots, business-view perspective, KIND_EDGE
            _ek = structural_edge_key(_t, _c, SAMPLE_BUSINESS_VIEW)
            assert _ek.count(":") == 3, f"structural edge must have 4 slots: {_ek!r}"
            assert classify_key(_ek) == KIND_EDGE, f"misclassified structural edge: {_ek!r}"
            # Same table:column, different perspective → must classify differently
            assert classify_key(_ck) != classify_key(_ek), (
                f"column vertex and edge collided: {_ck!r} vs {_ek!r}"
            )
            n_edges += 1
            sample_edge_key = sample_edge_key or _ek
finally:
    _conn.close()

# Semantic edge — 6 slots, family 'semantic' (DEFERRED layer; format locked).
# Kept in lockstep with the key_scheme block in graph_metadata.json.
assert classify_key(SAMPLE_SEMANTIC_KEY) == KIND_SEMANTIC, (
    f"misclassified semantic edge: {SAMPLE_SEMANTIC_KEY!r}"
)

# Malformed keys (wrong slot count, or 6 slots without the 'semantic' family)
# must be rejected outright.
for _bad in ["no_delimiter", "two:slots", "a:b:c:d:e", "a:b:structural:d:e:f"]:
    try:
        classify_key(_bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"classify_key should have rejected {_bad!r}")

print(f"Table vertices  (3 slots)            : {n_tables} classified OK")
print(f"Column vertices (4 slots, 'system')  : {n_columns} classified OK")
print(f"Structural edges (4 slots, business) : {n_edges} classified OK")
print(f"Semantic edge   (6 slots, 'semantic'): 1 classified OK")
print(f"Sample table vertex  : {sample_table_key}")
print(f"Sample column vertex : {sample_column_key}")
print(f"Sample structural edge: {sample_edge_key}")
print(f"Sample semantic edge : {SAMPLE_SEMANTIC_KEY}")
print("Slot-length structural parsing assertions passed (offline)")

print("\n" + "=" * 60)
print("DEMO COMPLETE")
print("=" * 60)
