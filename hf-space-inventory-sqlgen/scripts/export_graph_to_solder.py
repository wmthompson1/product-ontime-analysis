"""
export_graph_to_solder.py
=========================
Exports the ArangoDB `contains` edge topology to a flat column-catalog JSON,
and optionally validates all approved SolderEngine bindings against that catalog.

Usage
-----
  python export_graph_to_solder.py                  # print JSON to stdout
  python export_graph_to_solder.py --output         # write solder_catalog.json next to this script
  python export_graph_to_solder.py --output out.json
  python export_graph_to_solder.py --dry-run        # preview without writing
  python export_graph_to_solder.py --validate       # cross-check approved bindings
  python export_graph_to_solder.py --output --validate

Exit codes
----------
  0  success (or --validate with zero mismatches)
  1  connection failure, or --validate found mismatches
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(SCRIPTS_DIR)
DEFAULT_OUTPUT = os.path.join(SCRIPTS_DIR, "solder_catalog.json")

sys.path.insert(0, HF_DIR)


def _get_arango_db():
    """Connect to ArangoDB using the same env-var convention as graph_sync.py."""
    from graph_sync import get_arango_client, get_arango_db as _get_db
    client = get_arango_client()
    return _get_db(client)


def fetch_solder_catalog(db) -> List[Dict[str, Any]]:
    """Run an AQL projection over the `contains` edge collection.

    Each edge goes from a `tables` vertex (_from) to a `columns` vertex (_to).
    We resolve both endpoints via DOCUMENT() and map to the flat catalog shape.

    Returns a list of dicts with keys:
        qualified_name  — "TABLE_NAME.column_name"
        table_name      — from the tables vertex
        column_name     — from the columns vertex
        data_type       — from the columns vertex (empty string if absent)
        primary_key     — bool, from the columns vertex `primary_key` field
        not_null        — bool, from the columns vertex `notnull` field
    """
    aql = """
    FOR e IN contains
        LET tbl = DOCUMENT(e._from)
        LET col = DOCUMENT(e._to)
        FILTER tbl != null AND col != null
        RETURN {
            table_name:  tbl.table_name,
            column_name: col.column_name,
            column_type: col.column_type,
            primary_key: col.primary_key,
            notnull:     col.notnull
        }
    """
    cursor = db.aql.execute(aql)
    rows: List[Dict[str, Any]] = []
    for doc in cursor:
        tbl = (doc.get("table_name") or "").strip()
        col = (doc.get("column_name") or "").strip()
        if not tbl or not col:
            continue
        rows.append({
            "qualified_name": f"{tbl}.{col}",
            "table_name":     tbl,
            "column_name":    col,
            "data_type":      doc.get("column_type") or "",
            "primary_key":    bool(doc.get("primary_key")),
            "not_null":       bool(doc.get("notnull")),
        })
    return rows


def validate_bindings(catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cross-reference every approved SolderEngine binding against the catalog.

    Returns a list of mismatch dicts:
        {binding_key, unknown_tables: [str]}
    An empty list means all bindings are catalog-clean.
    """
    from solder_engine import SolderEngine

    catalog_tables = {row["table_name"].upper() for row in catalog}

    engine = SolderEngine()
    bindings = engine.load_approved_bindings()

    mismatches: List[Dict[str, Any]] = []
    for b in bindings:
        if not b.sql_text:
            continue
        referenced = engine._extract_tables_from_sql(b.sql_text)
        unknown = [t for t in referenced if t.upper() not in catalog_tables]
        if unknown:
            mismatches.append({
                "binding_key":    b.binding_key,
                "unknown_tables": unknown,
            })
    return mismatches


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export ArangoDB graph topology to a Solder column catalog JSON."
    )
    parser.add_argument(
        "--output",
        nargs="?",
        const=DEFAULT_OUTPUT,
        default=None,
        metavar="PATH",
        help=(
            "Write catalog JSON to a file. "
            f"Defaults to {DEFAULT_OUTPUT!r} when flag is given without a path."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the catalog to stdout without writing any file.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="After exporting, validate all approved SolderEngine bindings against the catalog.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        db = _get_arango_db()
    except Exception as exc:
        print(f"ERROR: could not connect to ArangoDB: {exc}", file=sys.stderr)
        return 1

    try:
        catalog = fetch_solder_catalog(db)
    except Exception as exc:
        print(f"ERROR: AQL query failed: {exc}", file=sys.stderr)
        return 1

    table_set = {row["table_name"] for row in catalog}
    summary = f"Exported {len(catalog)} columns across {len(table_set)} tables"

    if args.dry_run:
        print(json.dumps(catalog, indent=2))
        print(summary, file=sys.stderr)
    elif args.output:
        out_path = args.output
        try:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(catalog, fh, indent=2)
            print(f"{summary} → {out_path}")
        except OSError as exc:
            print(f"ERROR: could not write to {out_path!r}: {exc}", file=sys.stderr)
            return 1
    else:
        print(json.dumps(catalog, indent=2))
        print(summary, file=sys.stderr)

    if args.validate:
        try:
            mismatches = validate_bindings(catalog)
        except Exception as exc:
            print(f"ERROR: validation failed: {exc}", file=sys.stderr)
            return 1

        if mismatches:
            print(f"\nVALIDATION FAILED — {len(mismatches)} binding(s) reference unknown tables:")
            for m in mismatches:
                print(f"  [{m['binding_key']}] unknown: {', '.join(m['unknown_tables'])}")
            return 1
        else:
            n = _count_approved_bindings()
            print(f"\nAll {n} approved binding(s) catalog-clean ✅")

    return 0


def _count_approved_bindings() -> int:
    """Return the count of approved bindings (best-effort, never raises)."""
    try:
        from solder_engine import SolderEngine
        return len(SolderEngine().load_approved_bindings())
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
