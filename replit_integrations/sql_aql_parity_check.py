"""sql_aql_parity_check.py — prove the SQLite graph tables == the live ArangoDB graph.

The companion ``sql_graph_parity_check.py`` proves *SQLite ↔ graph_metadata.json*
(SQL vs the static canonical file).  This check closes the loop on the *live*
side: it queries the ArangoDB graph collections with AQL, flattens each document
back into the canonical flat node/edge form (the only difference a server adds is
the volatile ``_rev``, which is dropped), and compares it field-for-field against
the SQLite source tables.  In other words it makes the parity a genuine **SQL vs
AQL** comparison rather than SQL vs a file.

Because the graph now lives in the flat ``sql_graph_nodes`` / ``sql_graph_edges``
tables, an AQL ``FOR d IN <collection> RETURN d`` is directly row-comparable to a
SQLite ``SELECT`` — so we get a flat, side-by-side report.  ArangoDB returns
documents unordered, so (unlike the JSON check) emission order is *not* asserted;
counts, ``_key`` sets, and every field are.

Exit codes:
    0  — parity holds, OR ArangoDB is unreachable/unconfigured (skipped), OR a
         required SQLite input is absent in --skip-on-missing
    1  — parity mismatch (a real drift between SQLite and the live graph)
    2  — a required SQLite input was missing (and --skip-on-missing not set)

Note: an unreachable ArangoDB is treated as a SKIP (exit 0), mirroring the
existing offline-tolerant bridge-health check, so CI without a graph still passes.
Use --require-arango to turn an unreachable graph into a failure instead.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import export_graph_metadata as ex  # noqa: E402
from sql_graph_parity_check import (  # noqa: E402
    _build_report,
    _clear_columnar_pair,
    _compare,
    _write_columnar_pair,
    _write_report_file,
    _write_status_report,
)

# Fields the ArangoDB server adds that are not part of the canonical document.
_SERVER_FIELDS = ("_rev",)

_REPORT_TITLE = "SQLite (SQL) <-> ArangoDB (AQL) parity report"


def flatten_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a canonical flat document: the AQL doc minus server-only fields."""
    return {k: v for k, v in doc.items() if k not in _SERVER_FIELDS}


def fetch_aql_graph(db: Any, node_col: str, edge_col: str) -> Tuple[List[dict], List[dict]]:
    """Pull every node/edge document from the live graph and flatten them."""
    nodes = [flatten_doc(d) for d in db.aql.execute(f"FOR d IN {node_col} RETURN d")]
    edges = [flatten_doc(d) for d in db.aql.execute(f"FOR d IN {edge_col} RETURN d")]
    return nodes, edges


def _default_arango_db():
    """Connect to the live ArangoDB using the canonical loader's connection rules."""
    from load_canonical_to_arango import open_db
    db, _url = open_db()
    return db


def _flat_report(node_diff: int, edge_diff: int, sql_counts, aql_counts) -> str:
    """A compact flattened report of the SQL vs AQL comparison."""
    lines = [
        f"{'collection':<14}{'SQLite':>10}{'ArangoDB':>12}{'Match':>9}",
        "-" * 45,
    ]
    for label, sql_n, aql_n, diff in (
        ("nodes", sql_counts[0], aql_counts[0], node_diff),
        ("edges", sql_counts[1], aql_counts[1], edge_diff),
    ):
        lines.append(f"{label:<14}{sql_n:>10}{aql_n:>12}{('OK' if diff == 0 else 'MISMATCH'):>9}")
    return "\n".join(lines)


def check_sql_aql_parity(
    db_path: str,
    *,
    arango_factory: Optional[Callable[[], Any]] = None,
    node_col: Optional[str] = None,
    edge_col: Optional[str] = None,
    skip_on_missing: bool = False,
    require_arango: bool = False,
    report_file: Optional[str] = None,
    csv_dir: Optional[str] = None,
    env_get: Callable[[str], Optional[str]] = os.environ.get,
) -> int:
    node_col = node_col or ex.NODE_COLLECTION
    edge_col = edge_col or ex.EDGE_COLLECTION

    if csv_dir:
        _clear_columnar_pair(csv_dir, "arango_graph")

    # --- SQLite source side -------------------------------------------------
    if not os.path.exists(db_path):
        msg = f"SQLite database not found: {db_path}"
        if skip_on_missing:
            print(f"[sql_aql_parity] SKIP — {msg}")
            _write_status_report(report_file, _REPORT_TITLE, f"SKIP — {msg}")
            return 0
        print(f"[sql_aql_parity] ERROR — {msg}", file=sys.stderr)
        _write_status_report(report_file, _REPORT_TITLE, f"ERROR — {msg}")
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
                print(f"[sql_aql_parity] SKIP — {msg}")
                _write_status_report(report_file, _REPORT_TITLE, f"SKIP — {msg}")
                return 0
            print(f"[sql_aql_parity] ERROR — {msg}", file=sys.stderr)
            _write_status_report(report_file, _REPORT_TITLE, f"ERROR — {msg}")
            return 2
        sql_nodes = ex._load_nodes_from_sqlite(conn)
        sql_edges = ex._load_edges_from_sqlite(conn)
    finally:
        conn.close()

    # --- live AQL side ------------------------------------------------------
    if arango_factory is None and not env_get("ARANGO_HOST"):
        msg = "ArangoDB not configured (ARANGO_HOST not set)"
        if require_arango:
            print(f"[sql_aql_parity] FAIL — {msg}", file=sys.stderr)
            _write_status_report(report_file, _REPORT_TITLE, f"FAIL — {msg}")
            return 1
        print(f"[sql_aql_parity] SKIP — {msg}")
        _write_status_report(report_file, _REPORT_TITLE, f"SKIP — {msg}")
        return 0

    factory = arango_factory or _default_arango_db
    try:
        db = factory()
        aql_nodes, aql_edges = fetch_aql_graph(db, node_col, edge_col)
    except Exception as exc:  # noqa: BLE001 — connection/query failures are tolerated
        msg = f"could not reach the live graph: {type(exc).__name__}: {exc}"
        if require_arango:
            print(f"[sql_aql_parity] FAIL — {msg}", file=sys.stderr)
            _write_status_report(report_file, _REPORT_TITLE, f"FAIL — {msg}")
            return 1
        print(f"[sql_aql_parity] SKIP — {msg}")
        _write_status_report(report_file, _REPORT_TITLE, f"SKIP — {msg}")
        return 0

    if csv_dir:
        _write_columnar_pair(csv_dir, "arango_graph", aql_nodes, aql_edges)

    # --- field-by-field comparison (order not asserted: AQL is unordered) ----
    node_errors = _compare("nodes", sql_nodes, aql_nodes, check_order=False, left="SQLite", right="ArangoDB")
    edge_errors = _compare("edges", sql_edges, aql_edges, check_order=False, left="SQLite", right="ArangoDB")
    errors = node_errors + edge_errors

    report = _flat_report(
        node_diff=len(sql_nodes) - len(aql_nodes),
        edge_diff=len(sql_edges) - len(aql_edges),
        sql_counts=(len(sql_nodes), len(sql_edges)),
        aql_counts=(len(aql_nodes), len(aql_edges)),
    )
    print(report)

    if errors:
        status_line = (
            "[sql_aql_parity] FAIL — the SQLite graph tables do not match the live ArangoDB graph"
        )
    else:
        status_line = (
            f"[sql_aql_parity] OK — {len(sql_nodes)} nodes and {len(sql_edges)} edges "
            "match between SQLite (SQL) and ArangoDB (AQL)"
        )

    if report_file:
        _write_report_file(report_file, _build_report(
            title=_REPORT_TITLE,
            sources=[
                ("db", db_path),
                ("arango_node_collection", node_col),
                ("arango_edge_collection", edge_col),
            ],
            left_name="SQLite",
            right_name="ArangoDB",
            node_counts=(len(sql_nodes), len(aql_nodes)),
            edge_counts=(len(sql_edges), len(aql_edges)),
            node_errors=node_errors,
            edge_errors=edge_errors,
            status_line=status_line,
        ))

    if errors:
        print("[sql_aql_parity] FAIL — the SQLite graph tables do not match the live ArangoDB graph:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"[sql_aql_parity] OK — {len(sql_nodes)} nodes and {len(sql_edges)} edges "
        "match between SQLite (SQL) and ArangoDB (AQL)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=ex.DB_PATH, help="Path to manufacturing.db (default: %(default)s)")
    parser.add_argument("--node-collection", default=None, help="Override the Arango node collection name")
    parser.add_argument("--edge-collection", default=None, help="Override the Arango edge collection name")
    parser.add_argument(
        "--skip-on-missing",
        action="store_true",
        help="Exit 0 instead of erroring when the SQLite DB or graph tables are absent.",
    )
    parser.add_argument(
        "--require-arango",
        action="store_true",
        help="Treat an unreachable/unconfigured ArangoDB as a failure (exit 1) instead of a skip.",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Also write the parity report (count table + status) to this file.",
    )
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Also write columnar per-record CSVs (arango_graph_nodes.csv / "
        "arango_graph_edges.csv) of the live graph into this directory.",
    )
    args = parser.parse_args()
    return check_sql_aql_parity(
        args.db,
        node_col=args.node_collection,
        edge_col=args.edge_collection,
        skip_on_missing=args.skip_on_missing,
        require_arango=args.require_arango,
        report_file=args.report_file,
        csv_dir=args.csv_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
