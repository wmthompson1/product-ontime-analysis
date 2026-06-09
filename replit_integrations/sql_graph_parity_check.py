"""sql_graph_parity_check.py — prove graph_metadata.json == the SQLite graph tables.

The exporter (export_graph_metadata.py) materializes the canonical graph into the
``sql_graph_nodes`` / ``sql_graph_edges`` tables and then serializes
graph_metadata.json FROM those tables.  This check independently re-reads both
artifacts and asserts they agree node-for-node and edge-for-edge — so a stale or
hand-edited JSON (or a stale table) fails the build.

What is compared (the document-level ``synced_at`` is intentionally ignored — it
is a fresh timestamp on every run and is not stored in the tables):
  * row counts per collection
  * the set of ``_key`` values
  * every field of every node/edge, by ``_key``
  * the emission order (JSON order == ``ORDER BY ordinal`` read-back order)

Exit codes:
    0  — parity holds (or skipped because inputs are absent in --skip-on-missing)
    1  — parity mismatch
    2  — a required input was missing (and --skip-on-missing not set)
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import export_graph_metadata as ex  # noqa: E402


def _load_json_graph(path: str) -> tuple[List[dict], List[dict]]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["nodes"], doc["edges"]


def _index_by_key(items: List[dict]) -> Dict[str, dict]:
    return {it["_key"]: it for it in items}


def _compare(
    label: str,
    json_items: List[dict],
    db_items: List[dict],
    *,
    check_order: bool = True,
    left: str = "JSON",
    right: str = "SQLite",
) -> List[str]:
    """Compare two flat lists of node/edge dicts keyed by ``_key``.

    ``check_order`` asserts the two lists are in the same order — true for the
    JSON↔SQLite check (both are deterministically ordered by ``ordinal``), but
    false for the SQLite↔AQL check (ArangoDB returns documents unordered).
    ``left``/``right`` only label the two sides in error messages.
    """
    errors: List[str] = []
    j = _index_by_key(json_items)
    d = _index_by_key(db_items)

    if len(json_items) != len(j):
        errors.append(f"{label}: duplicate _key in JSON ({len(json_items)} rows, {len(j)} unique)")
    if len(db_items) != len(d):
        errors.append(f"{label}: duplicate _key in {right} ({len(db_items)} rows, {len(d)} unique)")
    if len(json_items) != len(db_items):
        errors.append(f"{label}: count mismatch — {left}={len(json_items)} {right}={len(db_items)}")

    only_json = sorted(set(j) - set(d))
    only_db = sorted(set(d) - set(j))
    if only_json:
        errors.append(f"{label}: {len(only_json)} _key(s) in {left} but not {right}, e.g. {only_json[:5]}")
    if only_db:
        errors.append(f"{label}: {len(only_db)} _key(s) in {right} but not {left}, e.g. {only_db[:5]}")

    for key in sorted(set(j) & set(d)):
        jd, dd = j[key], d[key]
        if jd != dd:
            fields = sorted(set(jd) | set(dd))
            bad = [f for f in fields if jd.get(f) != dd.get(f)]
            errors.append(
                f"{label}: field mismatch for {key!r} on {bad}: "
                f"{left.lower()}={ {f: jd.get(f) for f in bad} } {right.lower()}={ {f: dd.get(f) for f in bad} }"
            )

    if check_order and [it["_key"] for it in json_items] != [it["_key"] for it in db_items]:
        errors.append(f"{label}: emission order differs between {left} and {right} read-back")

    return errors


def check_parity(db_path: str, json_path: str, skip_on_missing: bool = False) -> int:
    if not os.path.exists(json_path):
        msg = f"graph JSON not found: {json_path}"
        if skip_on_missing:
            print(f"[sql_graph_parity] SKIP — {msg}")
            return 0
        print(f"[sql_graph_parity] ERROR — {msg}", file=sys.stderr)
        return 2

    if not os.path.exists(db_path):
        msg = f"SQLite database not found: {db_path}"
        if skip_on_missing:
            print(f"[sql_graph_parity] SKIP — {msg}")
            return 0
        print(f"[sql_graph_parity] ERROR — {msg}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if not {ex.SQL_GRAPH_NODES_TABLE, ex.SQL_GRAPH_EDGES_TABLE} <= existing:
            msg = (
                f"{ex.SQL_GRAPH_NODES_TABLE} / {ex.SQL_GRAPH_EDGES_TABLE} not present "
                "(run export_graph_metadata.py to materialize them)"
            )
            if skip_on_missing:
                print(f"[sql_graph_parity] SKIP — {msg}")
                return 0
            print(f"[sql_graph_parity] ERROR — {msg}", file=sys.stderr)
            return 2
        db_nodes = ex._load_nodes_from_sqlite(conn)
        db_edges = ex._load_edges_from_sqlite(conn)
    finally:
        conn.close()

    json_nodes, json_edges = _load_json_graph(json_path)

    errors = _compare("nodes", json_nodes, db_nodes)
    errors += _compare("edges", json_edges, db_edges)

    if errors:
        print("[sql_graph_parity] FAIL — graph_metadata.json does not match the SQLite graph tables:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"[sql_graph_parity] OK — {len(json_nodes)} nodes and {len(json_edges)} edges "
        "match between SQLite and graph_metadata.json"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=ex.DB_PATH, help="Path to manufacturing.db (default: %(default)s)")
    parser.add_argument("--json", default=ex.JSON_PATH, help="Path to graph_metadata.json (default: %(default)s)")
    parser.add_argument(
        "--skip-on-missing",
        action="store_true",
        help="Exit 0 instead of erroring when the DB, JSON, or tables are absent.",
    )
    args = parser.parse_args()
    return check_parity(args.db, args.json, skip_on_missing=args.skip_on_missing)


if __name__ == "__main__":
    sys.exit(main())
