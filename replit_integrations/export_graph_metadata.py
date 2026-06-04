#!/usr/bin/env python3
"""
export_graph_metadata.py — Export the structural containment graph from SQLite,
in the exact key/edge format used by the live ArangoDB ``manufacturing_graph``.

The live graph's physical layer has only two node types — **tables** and
**columns** — connected by a CONTAINS edge (table → column) in the
``manufacturing_graph_edges`` edge collection. Semantic context (perspective,
intent, concept, weight) lives as edge properties on the semantic layer, never
as nodes, and is out of scope here.

Live-graph format (matched verbatim — names preserve their source case):
    table vertex   _key : "{table_name}"                     e.g. "dbo.INVENTORY_BALANCE"
                   _id  : "tables/{table_name}"
    column vertex  _key : "column::{table_name}.{column_name}"
                   _id  : "columns/column::{table_name}.{column_name}"
    contains edge  _from: "tables/{table_name}"
                   _to  : "columns/column::{table_name}.{column_name}"
                   edge_type: "CONTAINS"  (+ table_name, column_name; no predicate)

This export reads the *local* prototype SQLite (a small subset of the full live
graph), so it emits the same shape with whatever table/column names the local
catalog provides.

Build order (matches how the graph is assembled):
    1. table nodes     — from schema_nodes WHERE table_type = 'Table'
    2. column nodes     — from PRAGMA table_info(<table>) for each table
    3. contains edges   — table --CONTAINS--> column

Outputs, written next to this script:
    graph_triples.tsv   — flat (subject, predicate, object) triples
    graph_metadata.json — node/edge graph document with per-collection counts

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

# Live-graph collection names (parity targets).
TABLES_COLLECTION = "tables"
COLUMNS_COLLECTION = "columns"
EDGE_COLLECTION = "manufacturing_graph_edges"
EDGE_TYPE = "CONTAINS"


# ---------------------------------------------------------------------------
# Key builders — match the live ArangoDB graph verbatim (no case folding).
# ---------------------------------------------------------------------------

def table_key(table_name: str) -> str:
    """Live format: the raw table name, e.g. ``dbo.INVENTORY_BALANCE``."""
    return table_name


def column_key(table_name: str, column_name: str) -> str:
    """Live format: ``column::{table_name}.{column_name}`` (source case kept)."""
    return f"column::{table_name}.{column_name}"


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
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "sqlite:hf-space-inventory-sqlgen/app_schema/manufacturing.db",
        "description": (
            "Structural containment graph exported from SQLite in the live "
            "manufacturing_graph format (tables + columns + CONTAINS edges)."
        ),
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
    except OSError as exc:
        print(f"ERROR: failed to write export artifacts: {exc}", file=sys.stderr)
        return 1

    print("Structural containment graph exported from SQLite (live-graph format)")
    print(f"  triples : {TRIPLES_PATH}  ({len(edges)} {EDGE_TYPE} rows)")
    print(f"  graph   : {JSON_PATH}")
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
