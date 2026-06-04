#!/usr/bin/env python3
"""
export_graph_metadata.py — Export the structural containment graph from SQLite.

Mirrors the *physical* layer of the ArangoDB ``manufacturing_graph`` — the only
two node types in that graph are **tables** and **columns**, connected by
``has_column`` (the ``contains`` edge: table → column). Semantic context
(perspective, intent, concept, weight) is carried as edge properties on the
*semantic* layer, never as nodes, and is intentionally out of scope here.

Build order (matches how the graph is assembled):
    1. table nodes     — from schema_nodes WHERE table_type = 'Table'
    2. column nodes     — from PRAGMA table_info(<table>) for each table
    3. has_column edges — table --has_column--> column

Outputs, written next to this script:
    graph_triples.tsv   — flat (subject, predicate, object) triples
    graph_metadata.json — node/edge graph document with per-collection counts

Vertex keys match the canonical helpers exactly (table::NAME, column::TABLE.COL,
both uppercase), so the JSON ``counts`` block is a true parity fingerprint
against the live ArangoDB collections.

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

# Import the canonical key/document helpers so vertex keys match the live graph.
if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)

from arangodb_helpers.manufacturing_graph_version_0_0_1 import (  # noqa: E402
    TABLES_COLLECTION,
    COLUMNS_COLLECTION,
    table_key,
    column_key,
)

DB_PATH = os.path.join(_HF_DIR, "app_schema", "manufacturing.db")
TRIPLES_PATH = os.path.join(_HERE, "graph_triples.tsv")
JSON_PATH = os.path.join(_HERE, "graph_metadata.json")

HAS_COLUMN = "has_column"


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
        tkey = table_key(tname)
        table_nodes.append(
            {
                "_id": f"{TABLES_COLLECTION}/{tkey}",
                "_key": tkey,
                "collection": TABLES_COLLECTION,
                "node_type": "table",
                "label": tname.strip().upper(),
                "table_name": tname,
                "description": trow["description"] or "",
            }
        )

        try:
            col_rows = conn.execute(f"PRAGMA table_info({tname})").fetchall()
        except sqlite3.Error:
            col_rows = []

        if not col_rows:
            integrity["tables_without_columns"].append(tname)
            continue

        for col in col_rows:
            ckey = column_key(tname, col["name"])
            column_nodes.append(
                {
                    "_id": f"{COLUMNS_COLLECTION}/{ckey}",
                    "_key": ckey,
                    "collection": COLUMNS_COLLECTION,
                    "node_type": "column",
                    "label": f"{tname.strip().upper()}.{col['name'].strip().upper()}",
                    "table_name": tname.strip().upper(),
                    "column_name": col["name"].strip().upper(),
                    "column_type": col["type"] or "TEXT",
                    "notnull": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                    "parent_table_key": tkey,
                }
            )

    return table_nodes, column_nodes, integrity


def _build_has_column_edges(column_nodes: list[dict]) -> list[dict]:
    """One has_column edge per column: parent table --has_column--> column."""
    edges: list[dict] = []
    for c in column_nodes:
        edges.append(
            {
                "_from": f"{TABLES_COLLECTION}/{c['parent_table_key']}",
                "_to": c["_id"],
                "predicate": HAS_COLUMN,
                "edge_type": "CONTAINS",
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
            "Structural containment graph exported from SQLite (parity view of the "
            "ArangoDB manufacturing_graph physical layer: tables + columns + has_column)."
        ),
        "counts": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "nodes_by_type": {"table": len(table_nodes), "column": len(column_nodes)},
            "edges_by_predicate": {HAS_COLUMN: len(edges)},
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
        lines.append("\t".join([e["_from"], e["predicate"], e["_to"]]))
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

    edges = _build_has_column_edges(column_nodes)
    doc = _build_graph_document(table_nodes, column_nodes, edges, integrity)

    try:
        _write_triples(edges, TRIPLES_PATH)
        _write_json(doc, JSON_PATH)
    except OSError as exc:
        print(f"ERROR: failed to write export artifacts: {exc}", file=sys.stderr)
        return 1

    print("Structural containment graph exported from SQLite")
    print(f"  triples : {TRIPLES_PATH}  ({len(edges)} has_column rows)")
    print(f"  graph   : {JSON_PATH}")
    print(f"  nodes   : {doc['counts']['nodes_total']}  ({len(table_nodes)} tables, {len(column_nodes)} columns)")
    print(f"  edges   : {doc['counts']['edges_total']}  ({HAS_COLUMN})")
    if integrity["tables_without_columns"]:
        print(
            f"  WARN    : {len(integrity['tables_without_columns'])} registered table(s) "
            f"had no PRAGMA columns: {', '.join(integrity['tables_without_columns'])}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
