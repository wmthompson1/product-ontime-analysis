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

# Fixed 6-slot composite key template — every key has EXACTLY 6 ':'-delimited
# slots, parsed by fixed position (no prefix tag):
#     table : column|entity : family : perspective : predicate|none : unique_id|none
#       0          1            2          3              4               5
#     table node       table:entity:structural:system:none:none
#     column node      table:column:structural:system:none:none
#     structural edge  table:column:structural:system:has_column:UNIQUE_ID
#     semantic edge    table:column:semantic:<view>:resolves_to:UNIQUE_ID   (DEFERRED v2)
#
# NODE iff slot[4]=='none' and slot[5]=='none' (table node if slot[1]=='entity',
# else column node); otherwise EDGE, whose family is slot[2]. Reserved tokens:
# 'entity' (no column may be named it), 'none' (no column/table may be named it),
# 'system' (no business view may be named it).
FAMILY_STRUCTURAL = "structural"
FAMILY_SEMANTIC = "semantic"
PERSPECTIVE_SYSTEM = "system"
PLACEHOLDER_ENTITY = "entity"
NONE_SLOT = "none"
SAMPLE_BUSINESS_VIEW = "Payables"
SAMPLE_PREDICATE = "has_column"
# Canonical examples — kept in lockstep with the key_scheme block embedded in
# graph_metadata.json / graph_metadata_canonical_example.json.
SAMPLE_SEMANTIC_KEY = "PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_001"

KIND_TABLE = "table_node"
KIND_COLUMN = "column_node"
KIND_EDGE = "structural_edge"
KIND_SEMANTIC = "semantic_edge"


def _reject_delimiter(*parts):
    for p in parts:
        assert ":" not in str(p), f"component {p!r} must not contain the ':' delimiter"


def _abv(name):
    """First 3 alphanumeric chars, uppercased — the unified-uid abbreviation."""
    alnum = "".join(ch for ch in str(name) if ch.isalnum())
    return alnum[:3].upper()


def structural_unique_id(table, column, uniqifier=1):
    """Unified abbreviated structural uid: SYS_HAS_<tbl>_<col>_NNN."""
    return f"SYS_HAS_{_abv(table)}_{_abv(column)}_{uniqifier:03d}"


def table_vertex_key(table):
    _reject_delimiter(table)
    return f"{table}:{PLACEHOLDER_ENTITY}:{FAMILY_STRUCTURAL}:{PERSPECTIVE_SYSTEM}:{NONE_SLOT}:{NONE_SLOT}"


def column_vertex_key(table, column):
    _reject_delimiter(table, column)
    return f"{table}:{column}:{FAMILY_STRUCTURAL}:{PERSPECTIVE_SYSTEM}:{NONE_SLOT}:{NONE_SLOT}"


def structural_edge_key(table, column, unique_id, predicate=SAMPLE_PREDICATE):
    _reject_delimiter(table, column, unique_id, predicate)
    return f"{table}:{column}:{FAMILY_STRUCTURAL}:{PERSPECTIVE_SYSTEM}:{predicate}:{unique_id}"


def classify_key(key):
    """Classify a composite key by its fixed 6 slot positions.

    Layout: table:column|entity:family:perspective:predicate|none:unique_id|none
        NODE  iff slot[4]=='none' and slot[5]=='none'
                table node if slot[1]=='entity', else column node
        EDGE  otherwise; family is slot[2] ('structural' | 'semantic')
    """
    tokens = key.split(":")
    if len(tokens) != 6 or any(t == "" for t in tokens):
        raise ValueError(f"Unparseable key (must be 6 non-empty slots): {key!r}")
    is_node = tokens[4] == NONE_SLOT and tokens[5] == NONE_SLOT
    if is_node:
        return KIND_TABLE if tokens[1] == PLACEHOLDER_ENTITY else KIND_COLUMN
    if tokens[2] == FAMILY_SEMANTIC:
        return KIND_SEMANTIC
    if tokens[2] == FAMILY_STRUCTURAL:
        return KIND_EDGE
    raise ValueError(f"Unparseable edge family in slot 2: {key!r}")


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
        # Table node — 6 slots, slot[1]=='entity', ends none:none -> KIND_TABLE
        _tk = table_vertex_key(_t)
        assert _tk.count(":") == 5, f"table node must have 6 slots: {_tk!r}"
        assert classify_key(_tk) == KIND_TABLE, f"misclassified table node: {_tk!r}"
        n_tables += 1
        sample_table_key = sample_table_key or _tk

        _quoted = '"' + _t.replace('"', '""') + '"'
        try:
            _cols = [c["name"] for c in _conn.execute(f"PRAGMA table_info({_quoted})")]
        except sqlite3.Error:
            _cols = []

        for _c in _cols:
            # Column node — 6 slots, slot[1]!='entity', ends none:none -> KIND_COLUMN
            _ck = column_vertex_key(_t, _c)
            assert _ck.count(":") == 5, f"column node must have 6 slots: {_ck!r}"
            assert classify_key(_ck) == KIND_COLUMN, f"misclassified column node: {_ck!r}"
            n_columns += 1
            sample_column_key = sample_column_key or _ck

            # Structural edge — 6 slots, predicate + unique_id filled -> KIND_EDGE
            # Unified abbreviated uid (SYS_HAS_<tbl>_<col>_NNN); the demo uses 001
            # since collision-safe uniqifier allocation lives in the exporter.
            _uid = structural_unique_id(_t, _c)
            _ek = structural_edge_key(_t, _c, _uid)
            assert _ek.count(":") == 5, f"structural edge must have 6 slots: {_ek!r}"
            assert classify_key(_ek) == KIND_EDGE, f"misclassified structural edge: {_ek!r}"
            # Same table:column — node vs edge differ only in slots 5-6, must NOT collide
            assert classify_key(_ck) != classify_key(_ek), (
                f"column node and edge collided: {_ck!r} vs {_ek!r}"
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

# Malformed keys (wrong slot count, empty slot, or unknown edge family) must be
# rejected outright.
for _bad in ["no_delimiter", "two:slots", "a:b:c:d:e", "a:b:c:d:e:f:g", "a::c:d:e:f", "a:b:bogus:d:e:f"]:
    try:
        classify_key(_bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"classify_key should have rejected {_bad!r}")

print(f"Table nodes     (6 slots, 'entity')   : {n_tables} classified OK")
print(f"Column nodes    (6 slots, none:none)  : {n_columns} classified OK")
print(f"Structural edges(6 slots, has_column) : {n_edges} classified OK")
print(f"Semantic edge   (6 slots, 'semantic') : 1 classified OK")
print(f"Sample table node    : {sample_table_key}")
print(f"Sample column node   : {sample_column_key}")
print(f"Sample structural edge: {sample_edge_key}")
print(f"Sample semantic edge : {SAMPLE_SEMANTIC_KEY}")
print("Fixed 6-slot composite-key parsing assertions passed (offline)")

print("\n" + "=" * 60)
print("DEMO COMPLETE")
print("=" * 60)
