#!/usr/bin/env python3
"""
export_graph_metadata.py — Export the structural containment graph from SQLite
in the canonical, readable **fixed 6-slot composite-key** scheme.

This file is the *canonical anchor* for the graph plan: it is self-describing
(it embeds the full key grammar in a ``key_scheme`` block) and is stamped with a
``metadata_version`` / ``milestone_name`` so canonical drafts can be frozen as
versioned snapshots (e.g. ``graph_metadata.v1.0.0.json``).

Fixed 6-slot template (delimiter ``:``; every key has EXACTLY 6 slots; a
component may never be empty or contain ``:`` or ``/``)::

    table : column|entity : family : perspective : predicate|none : unique_id|none
      0          1            2          3              4               5

Reserved tokens (the exporter hard-fails if a source name collides):
    entity   slot 1 — placeholder marking a TABLE node (a table has no column)
    none     slots 4-5 — placeholder marking a NODE (no predicate / unique_id)
    system   slot 3 — perspective reserved for the structural layer

Parse by fixed position — no prefix tag needed:
    NODE  iff slot[4]=='none' and slot[5]=='none'
            table node if slot[1]=='entity', else column node
    EDGE  otherwise; its family is slot[2] ('structural' | 'semantic')

    table node       PAYABLE:entity:structural:system:none:none
    column node      PAYABLE:INVOICE_ID:structural:system:none:none
    structural edge  PAYABLE:INVOICE_ID:structural:system:has_column:PAY_INV_CONTAINMENT
    semantic edge    PAYABLE_LINE:RECEIVER_ID:semantic:Payables:elevates:PAY_ELE_RCVR_JOIN_001  [DEFERRED v2]

v1 milestone scope (this export): the **structural footprint only** — table
nodes, column nodes, and the has_column backbone edge (table -> column). The
semantic layer is format-locked in the embedded ``key_scheme`` but deferred.

Build order (matches how the graph is assembled):
    1. table nodes      — from schema_nodes WHERE table_type = 'Table'
    2. column nodes     — from PRAGMA table_info(<table>) for each table
    3. has_column edges — table --has_column--> column

Outputs, written next to this script:
    graph_triples.tsv          — flat (subject, predicate, object) triples
    graph_metadata.json        — canonical (latest) graph document
    graph_metadata.v{V}.json   — frozen milestone snapshot (created once, never clobbered)

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
METADATA_VERSION = "1.0.0"
MILESTONE_NAME = "database_bound_unambiguous_slots"
SNAPSHOT_PATH = os.path.join(_HERE, f"graph_metadata.v{METADATA_VERSION}.json")

# ArangoDB collections (canonical target naming; single node + single edge set).
NODE_COLLECTION = "manufacturing_graph_node"
EDGE_COLLECTION = "manufacturing_graph_edge"

# Fixed 6-slot composite-key vocabulary.
FAMILY_STRUCTURAL = "structural"
FAMILY_SEMANTIC = "semantic"
PERSPECTIVE_SYSTEM = "system"
PLACEHOLDER_ENTITY = "entity"   # slot 1, marks a table node
NONE_SLOT = "none"              # slots 4-5, mark a node
KEY_DELIMITER = ":"
EDGE_PREDICATE_CONTAINS = "has_column"

# Characters a component may never contain: the delimiter and the ArangoDB
# collection separator (banned inside a _key). Empty components are also banned.
FORBIDDEN_IN_COMPONENT = (KEY_DELIMITER, "/")
# Tokens reserved by the grammar — a real schema name may never equal these,
# or slot-position parsing would become ambiguous.
RESERVED_COLUMN_NAMES = frozenset({PLACEHOLDER_ENTITY, NONE_SLOT})
RESERVED_TABLE_NAMES = frozenset({NONE_SLOT})


# ---------------------------------------------------------------------------
# Key builders — fixed 6-slot composite scheme.
# ---------------------------------------------------------------------------

def _assert_component_safe(*parts: str) -> None:
    """Fail loud if any name would break the composite-key grammar.

    Anti-drift guard: a name containing ':' or '/', or an empty name, would make
    the fixed-slot parser ambiguous, so we refuse to emit it rather than silently
    sanitising (which would lose fidelity with the source schema).
    """
    for p in parts:
        s = str(p)
        if s == "":
            raise ValueError("composite-key components may not be empty")
        for bad in FORBIDDEN_IN_COMPONENT:
            if bad in s:
                raise ValueError(
                    f"name {p!r} contains reserved character {bad!r}; "
                    "composite keys require ':'- and '/'-free components"
                )


def _assert_name_not_reserved(name: str, reserved: frozenset, role: str) -> None:
    """Reject a source name that collides with a reserved grammar token."""
    if str(name) in reserved:
        raise ValueError(
            f"{role} name {name!r} collides with a reserved token "
            f"({', '.join(sorted(reserved))}); rename it in the source schema"
        )


def _slots(*parts: str) -> str:
    return KEY_DELIMITER.join(parts)


def table_key(table_name: str) -> str:
    """Table node: ``table:entity:structural:system:none:none`` (6 slots)."""
    _assert_component_safe(table_name)
    _assert_name_not_reserved(table_name, RESERVED_TABLE_NAMES, "table")
    return _slots(
        table_name, PLACEHOLDER_ENTITY, FAMILY_STRUCTURAL,
        PERSPECTIVE_SYSTEM, NONE_SLOT, NONE_SLOT,
    )


def column_key(table_name: str, column_name: str) -> str:
    """Column node: ``table:column:structural:system:none:none`` (6 slots)."""
    _assert_component_safe(table_name, column_name)
    _assert_name_not_reserved(table_name, RESERVED_TABLE_NAMES, "table")
    _assert_name_not_reserved(column_name, RESERVED_COLUMN_NAMES, "column")
    return _slots(
        table_name, column_name, FAMILY_STRUCTURAL,
        PERSPECTIVE_SYSTEM, NONE_SLOT, NONE_SLOT,
    )


def contains_edge_unique_id(table_name: str, column_name: str) -> str:
    """Deterministic unique_id for a containment edge (slot 5).

    Derived from the table+column so it is reproducible across runs (no drift).
    NOTE: this is the full-name form (e.g. PAYABLE_INVOICE_ID_CONTAINMENT); the
    canonical example uses a hand-abbreviated PAY_INV_CONTAINMENT — an
    abbreviation scheme cannot be derived deterministically, so the generator
    emits the full-name form. Swap this one function to change the convention.
    """
    return f"{table_name}_{column_name}_CONTAINMENT"


def contains_edge_key(table_name: str, column_name: str) -> str:
    """Structural edge: ``table:column:structural:system:has_column:uid`` (6 slots)."""
    _assert_component_safe(table_name, column_name)
    uid = contains_edge_unique_id(table_name, column_name)
    _assert_component_safe(uid)
    return _slots(
        table_name, column_name, FAMILY_STRUCTURAL, PERSPECTIVE_SYSTEM,
        EDGE_PREDICATE_CONTAINS, uid,
    )


def table_id(table_name: str) -> str:
    return f"{NODE_COLLECTION}/{table_key(table_name)}"


def column_id(table_name: str, column_name: str) -> str:
    return f"{NODE_COLLECTION}/{column_key(table_name, column_name)}"


def contains_edge_id(table_name: str, column_name: str) -> str:
    return f"{EDGE_COLLECTION}/{contains_edge_key(table_name, column_name)}"


# ---------------------------------------------------------------------------
# Extraction — tables, then columns, then has_column edges
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
                "node_family": FAMILY_STRUCTURAL,
                "perspective": PERSPECTIVE_SYSTEM,
                "table_name": tname,
                "column_slot": PLACEHOLDER_ENTITY,
                "predicate": NONE_SLOT,
                "unique_id": NONE_SLOT,
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
                    "node_family": FAMILY_STRUCTURAL,
                    "perspective": PERSPECTIVE_SYSTEM,
                    "table_name": tname,
                    "column_name": cname,
                    "predicate": NONE_SLOT,
                    "unique_id": NONE_SLOT,
                    "column_type": col["type"] or "TEXT",
                    "notnull": bool(col["notnull"]),
                    "default_value": col["dflt_value"],
                    "primary_key": bool(col["pk"]),
                }
            )

    return table_nodes, column_nodes, integrity


def _build_contains_edges(column_nodes: list[dict]) -> list[dict]:
    """One has_column edge per column: parent table --has_column--> column."""
    edges: list[dict] = []
    for c in column_nodes:
        tname = c["table_name"]
        cname = c["column_name"]
        edges.append(
            {
                "_id": contains_edge_id(tname, cname),
                "_key": contains_edge_key(tname, cname),
                "_from": table_id(tname),
                "_to": column_id(tname, cname),
                "edge_family": FAMILY_STRUCTURAL,
                "edge_type": EDGE_PREDICATE_CONTAINS,
                "perspective": PERSPECTIVE_SYSTEM,
                "unique_id": contains_edge_unique_id(tname, cname),
            }
        )
    return edges


# ---------------------------------------------------------------------------
# Canonical key-grammar spec (embedded so the artifact is self-describing)
# ---------------------------------------------------------------------------

def _key_scheme_spec() -> dict:
    """The full, locked fixed 6-slot composite-key grammar — incl. deferred layer.

    Embedding this in the artifact makes graph_metadata.json self-documenting:
    a reader can recover the entire naming plan from the file alone, which is
    the anti-drift anchor for this milestone.
    """
    return {
        "template": "table : column|entity : family : perspective : predicate|none : unique_id|none",
        "slots": 6,
        "fixed_width": True,
        "delimiter": KEY_DELIMITER,
        "forbidden_in_component": list(FORBIDDEN_IN_COMPONENT) + [""],
        "node_collection": NODE_COLLECTION,
        "edge_collection": EDGE_COLLECTION,
        "reserved_tokens": {
            PLACEHOLDER_ENTITY: "slot 2 (index 1): placeholder marking a TABLE node (a table has no column)",
            NONE_SLOT: "slots 5-6 (index 4-5): placeholder marking a NODE (no predicate / no unique_id)",
            PERSPECTIVE_SYSTEM: "slot 4 (index 3): perspective reserved for the structural layer",
        },
        "name_constraints": (
            "A real column may never be named 'entity' or 'none'; a real table "
            "may never be named 'none'; a business perspective may never be "
            "'system'. The exporter hard-fails if any source name collides."
        ),
        "parse_by": (
            "fixed slot positions: NODE iff slot[4]=='none' and slot[5]=='none' "
            "(table node if slot[1]=='entity', else column node); otherwise EDGE, "
            "whose family is slot[2]."
        ),
        "rules": [
            {
                "kind": "table_node",
                "slots": 6,
                "marker": "slot[1]=='entity' and slot[4:6]==['none','none']",
                "form": "table:entity:family:perspective:none:none",
                "example": "PAYABLE:entity:structural:system:none:none",
                "status": "active",
            },
            {
                "kind": "column_node",
                "slots": 6,
                "marker": "slot[1]!='entity' and slot[4:6]==['none','none']",
                "form": "table:column:family:perspective:none:none",
                "example": "PAYABLE:INVOICE_ID:structural:system:none:none",
                "status": "active",
            },
            {
                "kind": "structural_edge",
                "slots": 6,
                "marker": "slot[2]=='structural' and slot[4]!='none'",
                "form": "table:column:structural:system:predicate:unique_id",
                "example": "PAYABLE:INVOICE_ID:structural:system:has_column:PAY_INV_CONTAINMENT",
                "status": "active",
            },
            {
                "kind": "semantic_edge",
                "slots": 6,
                "marker": "slot[2]=='semantic' and slot[4]!='none'",
                "form": "table:column:semantic:perspective:predicate:unique_id",
                "example": "PAYABLE:INVOICE_ID:semantic:Payables:elevates:PAY_ELE_PAY_INV_001",
                "status": "deferred",
            },
        ],
        "unique_id_grammar": {
            "structural": "full-name {table}_{column}_CONTAINMENT — auto-generated, no registry",
            "semantic": {
                "form": "perspective(3)_edge_type(3)_table(3)_column|entity(3)_uniqifier(3)",
                "abbrev": "first 3 letters of each part, uppercased; collisions are expected and resolved by the uniqifier",
                "uniqifier": "allocated (not derived) per (perspective, edge_type, table, column|entity) tuple; default '001'",
                "edge_type_key_scope": "one edge_type key per perspective — the 3-char edge_type abbreviation is namespaced within its perspective, not global",
                "example": "PAY_ELE_PAY_INV_001",
                "status": "deferred",
            },
        },
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
        "metadata_version": METADATA_VERSION,
        "milestone_name": MILESTONE_NAME,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source": "sqlite:hf-space-inventory-sqlgen/app_schema/manufacturing.db",
        "description": (
            "Canonical structural containment graph exported from SQLite in the "
            "fixed 6-slot composite-key scheme (table + column nodes + has_column "
            "edges). This milestone covers the physical schema footprint only; "
            "the semantic layer is format-locked in key_scheme but deferred."
        ),
        "key_scheme": _key_scheme_spec(),
        "graph": {
            "node_collection": NODE_COLLECTION,
            "edge_collection": EDGE_COLLECTION,
        },
        "counts": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "nodes_by_type": {"table": len(table_nodes), "column": len(column_nodes)},
            "edges_by_type": {EDGE_PREDICATE_CONTAINS: len(edges)},
        },
        "integrity": integrity,
        "graph_nodes": nodes,
        "graph_edges": edges,
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

    print(f"Canonical graph exported (fixed 6-slot scheme, {MILESTONE_NAME})")
    print(f"  triples : {TRIPLES_PATH}  ({len(edges)} {EDGE_PREDICATE_CONTAINS} rows)")
    print(f"  graph   : {JSON_PATH}")
    print(f"  {snapshot_action}")
    print(f"  nodes   : {doc['counts']['nodes_total']}  ({len(table_nodes)} tables, {len(column_nodes)} columns)")
    print(f"  edges   : {doc['counts']['edges_total']}  ({EDGE_PREDICATE_CONTAINS} in {EDGE_COLLECTION})")
    if integrity["tables_without_columns"]:
        print(
            f"  WARN    : {len(integrity['tables_without_columns'])} registered table(s) "
            f"had no PRAGMA columns: {', '.join(integrity['tables_without_columns'])}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
