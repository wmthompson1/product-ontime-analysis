#!/usr/bin/env python3
"""
export_graph_metadata.py — Export the structural containment graph from SQLite
in the canonical, readable **composite-key** scheme.

This file is the *canonical anchor* for the graph plan: it is self-describing
(it embeds the full key grammar in a ``key_scheme`` block) and is stamped with a
``schema_version`` / ``milestone`` so canonical drafts can be frozen as
versioned snapshots (e.g. ``graph_metadata.v1.json``).

Composite key grammar (delimiter ``:``; a component may never contain ``:`` or
``/``; the perspective ``system`` is reserved for the structural layer):

    table vertex          table:family:perspective                       (3 slots)
                          e.g. "EMPLOYEE:structural:system"
    column vertex         table:column:family:perspective                (4 slots, perspective == 'system')
                          e.g. "certification:cert_id:structural:system"
    core structural edge  table:column:family:perspective                (4 slots, perspective == a business view)   [DEFERRED to v2]
                          e.g. "certification:cert_id:structural:payable"
    semantic edge         table:column:family:perspective:predicate:uid  (6 slots, family == 'semantic')             [DEFERRED to v2]
                          e.g. "PAYABLE:INVOICE_ID:semantic:payable:elevates:PAY_ELE_PAY_INV_001"

The ``intent`` slot is DEFERRED — it is not bound to the physical schema
footprint, so it is intentionally absent from these keys for now.

v1 milestone scope (this export): the **structural footprint only** — table
vertices, column vertices, and the CONTAINS backbone edge (table → column).
Perspective-scoped structural edges and semantic edges are deferred to v2 and
documented in the embedded ``key_scheme`` so the grammar is locked regardless.

Build order (matches how the graph is assembled):
    1. table nodes      — from schema_nodes WHERE table_type = 'Table'
    2. column nodes     — from PRAGMA table_info(<table>) for each table
    3. contains edges   — table --CONTAINS--> column

Outputs, written next to this script:
    graph_triples.tsv      — flat (subject, predicate, object) triples
    graph_metadata.json    — canonical (latest) graph document
    graph_metadata.v{N}.json — frozen milestone snapshot (created once, never clobbered)

Run from the repo root:
    python replit_integrations/export_graph_metadata.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_HF_DIR = os.path.join(_REPO_ROOT, "hf-space-inventory-sqlgen")

DB_PATH = os.path.join(_HF_DIR, "app_schema", "manufacturing.db")
TRIPLES_PATH = os.path.join(_HERE, "graph_triples.tsv")
JSON_PATH = os.path.join(_HERE, "graph_metadata.json")

# Canonical milestone identity — bump these to freeze a new snapshot.
SCHEMA_VERSION = 1
MILESTONE = "v1-structural-composite"
SNAPSHOT_PATH = os.path.join(_HERE, f"graph_metadata.v{SCHEMA_VERSION}.json")

# Vertex collections.
TABLES_COLLECTION = "tables"
COLUMNS_COLLECTION = "columns"
EDGE_COLLECTION = "contains"
EDGE_TYPE = "CONTAINS"

# Composite-key vocabulary.
FAMILY_STRUCTURAL = "structural"
PERSPECTIVE_SYSTEM = "system"
KEY_DELIMITER = ":"
# Characters a component may never contain: the delimiter, and the ArangoDB
# collection separator (banned inside a _key).
FORBIDDEN_IN_COMPONENT = (KEY_DELIMITER, "/")


# ---------------------------------------------------------------------------
# Key builders — canonical composite scheme.
# ---------------------------------------------------------------------------

def _assert_component_safe(*parts: str) -> None:
    """Fail loud if any name would break the composite-key grammar.

    Anti-drift guard: a table/column name containing ':' or '/' would make the
    slot-length parser ambiguous, so we refuse to emit it rather than silently
    sanitising (which would lose fidelity with the source schema).
    """
    for p in parts:
        for bad in FORBIDDEN_IN_COMPONENT:
            if bad in str(p):
                raise ValueError(
                    f"name {p!r} contains reserved character {bad!r}; "
                    "composite keys require ':'- and '/'-free components"
                )


def table_key(table_name: str) -> str:
    """Table vertex: ``table:structural:system`` (3 slots, source case kept)."""
    _assert_component_safe(table_name)
    return f"{table_name}{KEY_DELIMITER}{FAMILY_STRUCTURAL}{KEY_DELIMITER}{PERSPECTIVE_SYSTEM}"


def column_key(table_name: str, column_name: str) -> str:
    """Column vertex: ``table:column:structural:system`` (4 slots, source case kept)."""
    _assert_component_safe(table_name, column_name)
    return (
        f"{table_name}{KEY_DELIMITER}{column_name}"
        f"{KEY_DELIMITER}{FAMILY_STRUCTURAL}{KEY_DELIMITER}{PERSPECTIVE_SYSTEM}"
    )


def table_id(table_name: str) -> str:
    return f"{TABLES_COLLECTION}/{table_key(table_name)}"


def column_id(table_name: str, column_name: str) -> str:
    return f"{COLUMNS_COLLECTION}/{column_key(table_name, column_name)}"


# ---------------------------------------------------------------------------
# Extraction — tables, then columns, then contains edges
# ---------------------------------------------------------------------------

def _fetch_structure(conn: sqlite3.Connection) -> tuple[list[dict], list[dict], dict]:
    """Return (table_nodes, column_nodes, integrity) from SQLite.

    Tables come from the schema_nodes registry; columns come from PRAGMA
    table_info run against each registered table. Tables that cannot be
    PRAGMA'd (views, or dropped between registry and DB) are recorded in the
    integrity report rather than failing the export.
    """
    conn.row_factory = sqlite3.Row
    integrity = {"tables_without_columns": []}

    table_rows = conn.execute(
        "SELECT table_name, description FROM schema_nodes "
        "WHERE table_type = 'Table' ORDER BY table_name"
    ).fetchall()

    table_nodes: list[dict] = []
    column_nodes: list[dict] = []

    for trow in table_rows:
        tname = trow["table_name"]
        table_nodes.append(
            {
                "_id": table_id(tname),
                "_key": table_key(tname),
                "node_type": "table",
                "table_name": tname,
                "description": trow["description"] or "",
            }
        )

        try:
            # Quote the identifier so dotted/live-format names (e.g. dbo.X)
            # are not parsed as schema.table by PRAGMA. "" escapes a literal ".
            quoted = '"' + tname.replace('"', '""') + '"'
            col_rows = conn.execute(f"PRAGMA table_info({quoted})").fetchall()
        except sqlite3.Error:
            col_rows = []

        if not col_rows:
            integrity["tables_without_columns"].append(tname)
            continue

        for col in col_rows:
            cname = col["name"]
            column_nodes.append(
                {
                    "_id": column_id(tname, cname),
                    "_key": column_key(tname, cname),
                    "node_type": "column",
                    "table_name": tname,
                    "column_name": cname,
                    "column_type": col["type"] or "TEXT",
                    "notnull": bool(col["notnull"]),
                    "default_value": col["dflt_value"],
                    "primary_key": bool(col["pk"]),
                }
            )

    return table_nodes, column_nodes, integrity


def _build_contains_edges(column_nodes: list[dict]) -> list[dict]:
    """One CONTAINS edge per column: parent table --CONTAINS--> column."""
    edges: list[dict] = []
    for c in column_nodes:
        tname = c["table_name"]
        cname = c["column_name"]
        edges.append(
            {
                "_from": table_id(tname),
                "_to": column_id(tname, cname),
                "edge_type": EDGE_TYPE,
                "table_name": tname,
                "column_name": cname,
            }
        )
    return edges


# ---------------------------------------------------------------------------
# Canonical key-grammar spec (embedded so the artifact is self-describing)
# ---------------------------------------------------------------------------

def _key_scheme_spec() -> dict:
    """The full, locked composite-key grammar — including deferred layers.

    Embedding this in the artifact makes graph_metadata.json self-documenting:
    a reader can recover the entire naming plan from the file alone, which is
    the anti-drift anchor for this milestone.
    """
    return {
        "delimiter": KEY_DELIMITER,
        "forbidden_in_component": list(FORBIDDEN_IN_COMPONENT),
        "reserved_perspective": PERSPECTIVE_SYSTEM,
        "families": [FAMILY_STRUCTURAL, "semantic"],
        "deferred_slots": ["intent"],
        "parse_by": "slot_count + terminal/family tokens (no prefix tag)",
        "rules": [
            {
                "kind": "table_vertex",
                "slots": 3,
                "form": "table:family:perspective",
                "example": "EMPLOYEE:structural:system",
                "status": "active",
            },
            {
                "kind": "column_vertex",
                "slots": 4,
                "perspective": PERSPECTIVE_SYSTEM,
                "form": "table:column:family:perspective",
                "example": "certification:cert_id:structural:system",
                "status": "active",
            },
            {
                "kind": "core_structural_edge",
                "slots": 4,
                "perspective": "<business_view>",
                "form": "table:column:family:perspective",
                "example": "certification:cert_id:structural:payable",
                "status": "deferred",
            },
            {
                "kind": "semantic_edge",
                "slots": 6,
                "family": "semantic",
                "form": "table:column:family:perspective:predicate:unique_id",
                "example": "PAYABLE:INVOICE_ID:semantic:payable:elevates:PAY_ELE_PAY_INV_001",
                "status": "deferred",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def _build_graph_document(
    table_nodes: list[dict],
    column_nodes: list[dict],
    edges: list[dict],
    integrity: dict,
) -> dict:
    nodes = table_nodes + column_nodes
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone": MILESTONE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "sqlite:hf-space-inventory-sqlgen/app_schema/manufacturing.db",
        "description": (
            "Canonical structural containment graph exported from SQLite in the "
            "composite-key scheme (tables + columns + CONTAINS edges). v1 "
            "milestone covers the physical schema footprint only."
        ),
        "key_scheme": _key_scheme_spec(),
        "graph": {
            "vertex_collections": [TABLES_COLLECTION, COLUMNS_COLLECTION],
            "edge_collection": EDGE_COLLECTION,
        },
        "counts": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "nodes_by_type": {"table": len(table_nodes), "column": len(column_nodes)},
            "edges_by_type": {EDGE_TYPE: len(edges)},
        },
        "integrity": integrity,
        "nodes": nodes,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _write_triples(edges: list[dict], path: str) -> None:
    lines = ["subject\tpredicate\tobject"]
    for e in edges:
        lines.append("\t".join([e["_from"], e["edge_type"], e["_to"]]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _write_json(doc: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.path.exists(DB_PATH):
        print(f"ERROR: manufacturing.db not found at {DB_PATH}", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            table_nodes, column_nodes, integrity = _fetch_structure(conn)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"ERROR: failed to read schema from SQLite: {exc}", file=sys.stderr)
        return 1

    edges = _build_contains_edges(column_nodes)
    doc = _build_graph_document(table_nodes, column_nodes, edges, integrity)

    try:
        _write_triples(edges, TRIPLES_PATH)
        _write_json(doc, JSON_PATH)
        # Freeze the milestone snapshot once; never clobber a frozen canonical.
        if os.path.exists(SNAPSHOT_PATH):
            snapshot_action = f"snapshot kept (already frozen): {SNAPSHOT_PATH}"
        else:
            _write_json(doc, SNAPSHOT_PATH)
            snapshot_action = f"snapshot frozen: {SNAPSHOT_PATH}"
    except OSError as exc:
        print(f"ERROR: failed to write export artifacts: {exc}", file=sys.stderr)
        return 1

    print(f"Canonical graph exported (composite-key scheme, {MILESTONE})")
    print(f"  triples : {TRIPLES_PATH}  ({len(edges)} {EDGE_TYPE} rows)")
    print(f"  graph   : {JSON_PATH}")
    print(f"  {snapshot_action}")
    print(f"  nodes   : {doc['counts']['nodes_total']}  ({len(table_nodes)} tables, {len(column_nodes)} columns)")
    print(f"  edges   : {doc['counts']['edges_total']}  ({EDGE_TYPE} in {EDGE_COLLECTION})")
    if integrity["tables_without_columns"]:
        print(
            f"  WARN    : {len(integrity['tables_without_columns'])} registered table(s) "
            f"had no PRAGMA columns: {', '.join(integrity['tables_without_columns'])}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
