"""reconstruct_containment_graph.py — rebuild ArangoDB containment graph from SQLite.

Reads all rows from ``schema_topology_metadata`` and upserts ``tables``,
``columns``, and ``contains`` collections in ArangoDB so the graph always
mirrors the SQLite source of truth.  This is a standalone recovery / bootstrap
tool — it is not a replacement for the live ``sync_watcher.py`` daemon.

Idempotent: re-running against an unchanged database produces no net change.
When a vertex or edge already exists with the same key, the document is
compared field-by-field (excluding volatile ``synced_at``); a write is only
issued when content actually differs.

Usage:
    python reconstruct_containment_graph.py [--dry-run]

Environment variables (matching graph_sync.py / app.py conventions):
    SQLITE_DB_PATH        Path to manufacturing.db  (default: ../app_schema/manufacturing.db
                          relative to the scripts/ directory)
    ARANGO_HOST           ArangoDB URL with port, e.g. https://host:8529
    ARANGO_USER           ArangoDB username (default: root)
    ARANGO_ROOT_PASSWORD  ArangoDB password (default: empty string)
    ARANGO_DB             Database / graph name (default: manufacturing_graph)

Exit codes:
    0  — success (including dry-run)
    1  — ArangoDB connection failure or missing database
    2  — unexpected runtime error
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Allow running from scripts/ without installing the package
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SPACE_DIR = os.path.dirname(_SCRIPTS_DIR)
if _SPACE_DIR not in sys.path:
    sys.path.insert(0, _SPACE_DIR)

# ---------------------------------------------------------------------------
# Paths / env
# ---------------------------------------------------------------------------

SQLITE_DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(_SCRIPTS_DIR, "..", "app_schema", "manufacturing.db"),
)

GRAPH_NAME = os.environ.get("ARANGO_DB", "manufacturing_graph")

# ---------------------------------------------------------------------------
# ArangoDB connection helpers (matches graph_sync.py)
# ---------------------------------------------------------------------------


def _get_arango_client():
    from arango import ArangoClient

    raw_host = (
        os.environ.get("ARANGO_HOST")
        or os.environ.get("DATABASE_HOST", "http://localhost:8529")
    ).strip()
    if "arangodb.cloud" in raw_host and ":" not in raw_host.split("//", 1)[-1]:
        raw_host = f"{raw_host}:8529"
    return ArangoClient(hosts=raw_host)


def _get_arango_db(client):
    db_name = os.environ.get("ARANGO_DB", "manufacturing_graph")
    username = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_ROOT_PASSWORD", "")

    try:
        sys_db = client.db("_system", username=username, password=password)
        if not sys_db.has_database(db_name):
            print(
                f"[ERROR] ArangoDB database {db_name!r} does not exist. "
                "Run graph_sync.py first to bootstrap the database.",
                file=sys.stderr,
            )
            sys.exit(1)
        return client.db(db_name, username=username, password=password)
    except Exception as exc:
        print(f"[ERROR] ArangoDB connection failed: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Collection / predicate constants
# ---------------------------------------------------------------------------

from arangodb_helpers.manufacturing_graph_version_0_0_1 import (
    TABLES_COLLECTION,
    COLUMNS_COLLECTION,
    CONTAINS_EDGE_COLLECTION,
    table_key,
    column_key,
    contains_edge_key,
    table_vertex,
    column_vertex,
    contains_edge,
)

_KNOWN_EDGE_PREDICATES = {"CONTAINS"}

_NODE_TYPE_TO_COLLECTION = {
    "table": TABLES_COLLECTION,
    "column": COLUMNS_COLLECTION,
}

# ---------------------------------------------------------------------------
# SQLite read
# ---------------------------------------------------------------------------


def _read_topology_rows(db_path: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, source_node_type, target_node_type,
                   source_key, target_key, edge_predicate, weight, notes
            FROM schema_topology_metadata
            ORDER BY id
            """
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(
            f"[ERROR] Could not read schema_topology_metadata: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Idempotent write helpers
# ---------------------------------------------------------------------------

_VOLATILE_FIELDS = {"synced_at", "_id", "_rev"}


def _content_differs(existing: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    """Return True if the stable (non-volatile) fields in *candidate* differ from
    those in *existing*.  Ignores _id, _rev, and synced_at so that timestamp
    churn never causes a spurious write.
    """
    for k, v in candidate.items():
        if k in _VOLATILE_FIELDS:
            continue
        if existing.get(k) != v:
            return True
    return False


def _idempotent_vertex(
    collection,
    key: str,
    doc: Dict[str, Any],
) -> str:
    """Insert or update vertex only when content differs.

    Returns:
        "inserted"  — new document created
        "updated"   — existing document had changed content and was updated
        "skipped"   — existing document content matches; no write issued
    """
    if collection.has(key):
        existing = collection.get(key)
        if _content_differs(existing, doc):
            collection.update(doc)
            return "updated"
        return "skipped"
    doc["_key"] = key
    collection.insert(doc)
    return "inserted"


def _idempotent_edge(
    collection,
    from_id: str,
    to_id: str,
    key: str,
    doc: Dict[str, Any],
) -> str:
    """Insert or update edge only when content differs.

    Returns: "inserted" | "updated" | "skipped"
    """
    if collection.has(key):
        existing = collection.get(key)
        if _content_differs(existing, doc):
            collection.update(doc)
            return "updated"
        return "skipped"
    doc["_key"] = key
    doc["_from"] = from_id
    doc["_to"] = to_id
    collection.insert(doc)
    return "inserted"


# ---------------------------------------------------------------------------
# Core reconstruction logic
# ---------------------------------------------------------------------------


def reconstruct(dry_run: bool = False) -> None:
    db_path = os.path.abspath(SQLITE_DB_PATH)

    if not os.path.exists(db_path):
        print(f"[ERROR] SQLite database not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    rows = _read_topology_rows(db_path)
    print(
        f"[reconstruct_containment_graph] rows read from schema_topology_metadata: {len(rows)}"
    )

    if not rows:
        print("[reconstruct_containment_graph] Nothing to reconstruct — table is empty.")
        return

    if dry_run:
        _run_dry(rows)
        return

    client = _get_arango_client()
    db = _get_arango_db(client)

    _ensure_collections(db)

    tables_coll = db.collection(TABLES_COLLECTION)
    columns_coll = db.collection(COLUMNS_COLLECTION)
    contains_coll = db.collection(CONTAINS_EDGE_COLLECTION)

    synced_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    vertices_upserted = 0
    edges_upserted = 0
    rows_skipped = 0

    for row in rows:
        src_type = row["source_node_type"]
        tgt_type = row["target_node_type"]
        src_key_val = row["source_key"]
        tgt_key_val = row["target_key"]
        predicate = row["edge_predicate"]

        if predicate not in _KNOWN_EDGE_PREDICATES:
            print(
                f"  [SKIP] row id={row['id']} unknown edge_predicate={predicate!r}",
                file=sys.stderr,
            )
            rows_skipped += 1
            continue

        src_coll_name = _NODE_TYPE_TO_COLLECTION.get(src_type)
        tgt_coll_name = _NODE_TYPE_TO_COLLECTION.get(tgt_type)

        if src_coll_name is None or tgt_coll_name is None:
            print(
                f"  [SKIP] row id={row['id']} unhandled node types "
                f"({src_type!r} → {tgt_type!r})",
                file=sys.stderr,
            )
            rows_skipped += 1
            continue

        if src_coll_name == TABLES_COLLECTION and tgt_coll_name == COLUMNS_COLLECTION:
            tbl_name = src_key_val
            col_name = tgt_key_val

            tbl_key = table_key(tbl_name)
            tbl_doc = table_vertex(tbl_name, synced_at=synced_at)
            result = _idempotent_vertex(tables_coll, tbl_key, tbl_doc)
            if result != "skipped":
                vertices_upserted += 1

            col_key = column_key(tbl_name, col_name)
            col_doc = column_vertex(tbl_name, col_name, synced_at=synced_at)
            result = _idempotent_vertex(columns_coll, col_key, col_doc)
            if result != "skipped":
                vertices_upserted += 1

            edge_key = contains_edge_key(tbl_name, col_name)
            edge_doc = contains_edge(tbl_name, col_name, synced_at=synced_at)
            from_id = edge_doc.pop("_from")
            to_id = edge_doc.pop("_to")
            result = _idempotent_edge(
                contains_coll, from_id, to_id, edge_key, edge_doc
            )
            if result != "skipped":
                edges_upserted += 1

        else:
            print(
                f"  [SKIP] row id={row['id']} no ArangoDB collection for "
                f"{src_type!r} → {tgt_type!r}",
                file=sys.stderr,
            )
            rows_skipped += 1

    print(
        f"[reconstruct_containment_graph] Done — "
        f"vertices upserted: {vertices_upserted}, "
        f"edges upserted: {edges_upserted}, "
        f"rows skipped: {rows_skipped}."
    )


def _run_dry(rows: List[Dict[str, Any]]) -> None:
    vertices_would_upsert = 0
    edges_would_upsert = 0
    rows_skipped = 0

    for row in rows:
        src_type = row["source_node_type"]
        tgt_type = row["target_node_type"]
        predicate = row["edge_predicate"]

        if predicate not in _KNOWN_EDGE_PREDICATES:
            print(f"  [DRY-RUN SKIP] unknown edge_predicate={predicate!r} (row id={row['id']})")
            rows_skipped += 1
            continue

        src_coll = _NODE_TYPE_TO_COLLECTION.get(src_type)
        tgt_coll = _NODE_TYPE_TO_COLLECTION.get(tgt_type)

        if src_coll is None or tgt_coll is None:
            print(
                f"  [DRY-RUN SKIP] unhandled node types {src_type!r} → {tgt_type!r} "
                f"(row id={row['id']})"
            )
            rows_skipped += 1
            continue

        if src_coll == TABLES_COLLECTION and tgt_coll == COLUMNS_COLLECTION:
            tbl_key_str = table_key(row["source_key"])
            col_key_str = column_key(row["source_key"], row["target_key"])
            edge_key_str = contains_edge_key(row["source_key"], row["target_key"])
            print(
                f"  [DRY-RUN] would upsert table vertex {tbl_key_str!r}, "
                f"column vertex {col_key_str!r}, "
                f"contains edge {edge_key_str!r}"
            )
            vertices_would_upsert += 2
            edges_would_upsert += 1
        else:
            print(
                f"  [DRY-RUN SKIP] no collection mapping for "
                f"{src_type!r} → {tgt_type!r} (row id={row['id']})"
            )
            rows_skipped += 1

    print(
        f"[reconstruct_containment_graph] DRY-RUN — "
        f"would upsert {vertices_would_upsert} vertex ops, "
        f"{edges_would_upsert} edge ops, "
        f"{rows_skipped} rows skipped."
    )


def _ensure_collections(db) -> None:
    for coll_name in (TABLES_COLLECTION, COLUMNS_COLLECTION):
        if not db.has_collection(coll_name):
            db.create_collection(coll_name)
    if not db.has_collection(CONTAINS_EDGE_COLLECTION):
        db.create_collection(CONTAINS_EDGE_COLLECTION, edge=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild ArangoDB tables/columns/contains collections "
            "from schema_topology_metadata in SQLite."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to ArangoDB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        reconstruct(dry_run=args.dry_run)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[ERROR] Unexpected failure: {exc}", file=sys.stderr)
        sys.exit(2)
