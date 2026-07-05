"""import_graph_metadata.py — restore sql_graph_* tables FROM the committed JSON.

Normal direction: SQLite ``sql_graph_nodes`` / ``sql_graph_edges`` are the source
of truth and ``export_graph_metadata.py`` serializes ``graph_metadata.json`` FROM
them (the JSON is provably a dump of those rows; ``sql_graph_parity_check.py``
gates that field-for-field).

This script is the DISASTER-RECOVERY inverse for one specific situation: the app
database (``manufacturing.db``) is gitignored, so when it is rebuilt from scratch
(``scripts/bootstrap_db.py``) the materialized graph rows are lost while the
committed JSON survives in git. The bridge feeds the exporter materializes from
(``schema_topology_metadata``, elevation rows, authored edges) are NOT part of the
bootstrap chain, so a fresh database cannot re-derive the frozen graph — the
committed JSON is the only remaining copy. Restoring the tables from it is a
faithful inversion of the dump, after which the parity gate passes by
construction *for this restore* while still catching any later drift.

Fail-closed rules:
  - refuses to run if ``sql_graph_nodes`` or ``sql_graph_edges`` already contain
    rows (never papers over real drift on a populated database) unless ``--force``
  - validates the JSON's own ``counts`` block against the actual arrays
  - verifies read-back counts after the load

Usage:
    python replit_integrations/import_graph_metadata.py [--db PATH] [--json PATH] [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Single source of truth for the table DDL — never duplicate it here.
from export_graph_metadata import SQL_GRAPH_DDL  # noqa: E402

DEFAULT_DB = os.path.join(
    _ROOT, "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db"
)
DEFAULT_JSON = os.path.join(_HERE, "graph_metadata.json")

NODE_COLUMNS = [
    "ordinal", "_key", "_id", "node_type", "node_family", "perspective",
    "table_name", "column_name", "column_slot", "concept_name", "concept_type",
    "domain", "synonyms", "tags", "computation_template", "binding_key",
    "concept_anchor", "logic_type", "predicate", "unique_id", "description",
    "column_type", "notnull", "default_value", "primary_key", "foreign_key",
]
EDGE_COLUMNS = [
    "ordinal", "_key", "_id", "_from", "_to", "edge_family", "edge_type",
    "perspective", "unique_id", "references_table", "references_column",
    "weight", "priority_weight", "field_component", "variable_name",
    "origin", "join_type",
]


def _fail(msg: str) -> "int":
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def _table_exists(cur, name: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _row_count(cur, name: str) -> int:
    if not _table_exists(cur, name):
        return 0
    return cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", default=DEFAULT_JSON)
    ap.add_argument("--force", action="store_true",
                    help="allow restoring over already-populated tables")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        return _fail(f"database not found: {args.db}")
    if not os.path.exists(args.json):
        return _fail(f"graph_metadata.json not found: {args.json}")

    with open(args.json, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    nodes = doc.get("nodes")
    edges = doc.get("edges")
    counts = doc.get("counts") or {}
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return _fail("malformed JSON: 'nodes' / 'edges' arrays missing")
    if not nodes or not edges:
        return _fail("malformed JSON: empty 'nodes' or 'edges' array")

    # The JSON must be internally consistent before we trust it as a source.
    want_nodes = counts.get("nodes_total")
    want_edges = counts.get("edges_total")
    if want_nodes != len(nodes):
        return _fail(
            f"counts.nodes_total={want_nodes} but nodes array has {len(nodes)}"
        )
    if want_edges != len(edges):
        return _fail(
            f"counts.edges_total={want_edges} but edges array has {len(edges)}"
        )
    for row, kind in ((nodes, "node"), (edges, "edge")):
        missing = [r.get("_key") or f"#{i}" for i, r in enumerate(row)
                   if not r.get("_key") or not r.get("_id")]
        if missing:
            return _fail(f"{kind} rows missing _key/_id, e.g. {missing[:3]}")

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    try:
        n_have = _row_count(cur, "sql_graph_nodes")
        e_have = _row_count(cur, "sql_graph_edges")
        if (n_have or e_have) and not args.force:
            return _fail(
                f"sql_graph tables are not empty (nodes={n_have}, edges={e_have}); "
                "refusing to overwrite a populated graph without --force. "
                "If the tables are merely stale, use the seed_elevations + "
                "export_graph_metadata path instead."
            )

        # Recreate with the CURRENT-generation DDL: a stale database may hold the
        # tables under an older CHECK constraint set (e.g. pre-concept/binding).
        cur.execute("DROP TABLE IF EXISTS sql_graph_nodes")
        cur.execute("DROP TABLE IF EXISTS sql_graph_edges")
        cur.executescript(SQL_GRAPH_DDL)

        def _bind(v):
            # list/dict JSON fields (e.g. concept synonyms/tags) are stored as
            # canonical JSON text in SQLite — same convention as the exporter.
            if isinstance(v, (list, dict)):
                return json.dumps(v)
            return v

        node_sql = (
            "INSERT INTO sql_graph_nodes ("
            + ", ".join(f'"{c}"' for c in NODE_COLUMNS)
            + ") VALUES (" + ",".join("?" * len(NODE_COLUMNS)) + ")"
        )
        for i, n in enumerate(nodes):
            vals = [i if c == "ordinal" else _bind(n.get(c)) for c in NODE_COLUMNS]
            cur.execute(node_sql, vals)

        edge_sql = (
            "INSERT INTO sql_graph_edges ("
            + ", ".join(f'"{c}"' for c in EDGE_COLUMNS)
            + ") VALUES (" + ",".join("?" * len(EDGE_COLUMNS)) + ")"
        )
        for i, e in enumerate(edges):
            vals = [i if c == "ordinal" else _bind(e.get(c)) for c in EDGE_COLUMNS]
            cur.execute(edge_sql, vals)

        n_now = _row_count(cur, "sql_graph_nodes")
        e_now = _row_count(cur, "sql_graph_edges")
        if n_now != len(nodes) or e_now != len(edges):
            conn.rollback()
            return _fail(
                f"read-back mismatch after load: nodes {n_now}/{len(nodes)}, "
                f"edges {e_now}/{len(edges)} — rolled back"
            )
        conn.commit()
        print(
            f"restored sql_graph_nodes={n_now} sql_graph_edges={e_now} "
            f"from {os.path.relpath(args.json, _ROOT)} "
            f"(schema_version={doc.get('schema_version')})"
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
