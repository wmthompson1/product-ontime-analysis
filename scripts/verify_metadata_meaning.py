#!/usr/bin/env python3
"""
verify_metadata_meaning.py
==========================
Two-sweep validation script that proves the semantic graph and the physical
SQLite schema are telling the same story end-to-end.

Sweep 1 — Intent-Driven Semantic Triple Benchmark
    Reads live ELEVATES edges from ArangoDB, reconstructs each triple
    (Subject intent → ELEVATES → Object concept), then confirms a matching
    APPROVED binding exists for that concept_anchor in the SQLite reviewer
    manifest.

Sweep 2 — AQL-to-SQLite Column Parity Matrix
    Fetches all `columns` vertex keys from ArangoDB (format: column::TABLE.COLUMN),
    parses TABLE and COLUMN from each key, then looks up the column in SQLite via
    metadata_query_templates.get_column_info().  Prints a parity matrix and exits
    non-zero if any column key cannot be resolved to a real SQLite column.

Usage
-----
    python scripts/verify_metadata_meaning.py
    python scripts/verify_metadata_meaning.py --skip-on-no-arango

The --skip-on-no-arango flag (or absent ARANGO_HOST env var) causes the script
to print SKIP and exit 0 rather than failing.

The --allow-sweep1-gaps flag is the escape hatch for Sweep 1: it downgrades
coverage gaps (concept anchors without an APPROVED SQL snippet) from a hard
failure to a warning, while still exiting 0. As of 2026-06-04 the nightly
graph-sync workflow runs WITHOUT this flag — every concept anchor now has an
approved snippet, so a new gap is a regression that must fail the build. Pass
--allow-sweep1-gaps (in CI, via the ALLOW_SWEEP1_GAPS=true repository variable)
only for a deliberate, temporary exception. Sweep 2 (column parity) always
hard-fails regardless of this flag.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup — make hf-space-inventory-sqlgen importable from any CWD
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_HF_DIR = os.path.join(_REPO_ROOT, "hf-space-inventory-sqlgen")

for _p in (_HF_DIR, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SQLITE_DB_PATH = os.path.join(_HF_DIR, "app_schema", "manufacturing.db")
MANIFEST_PATH = os.path.join(_HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arango_available() -> bool:
    return bool(os.environ.get("ARANGO_HOST"))


def _connect_arango():
    from graph_sync import get_arango_client, get_arango_db
    client = get_arango_client()
    return get_arango_db(client)


def _open_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hr(char: str = "-", width: int = 72) -> str:
    return char * width


# ---------------------------------------------------------------------------
# Sweep 1 — Intent-Driven Semantic Triple Benchmark
# ---------------------------------------------------------------------------

def sweep1_semantic_triple_benchmark(db, sqlite_conn: sqlite3.Connection) -> bool:
    """Read ELEVATES edges, reconstruct triples, verify approved bindings exist.

    Returns True when all triples checked have a matching APPROVED binding and
    at least one triple was verified.  Returns False on any failure.
    """
    from metadata_query_templates import get_ground_truth_bindings

    print()
    print(_hr("="))
    print("SWEEP 1 — Intent-Driven Semantic Triple Benchmark")
    print(_hr("="))

    # ── Fetch ELEVATES edges from ArangoDB ───────────────────────────────────
    try:
        aql = """
        FOR e IN elevates
            LET intent_doc  = DOCUMENT(e._from)
            LET concept_doc = DOCUMENT(e._to)
            RETURN {
                intent_key  : intent_doc._key,
                intent_name : intent_doc.intent_name,
                concept_key : concept_doc._key,
                concept_name: concept_doc.concept_name,
                weight      : e.weight
            }
        """
        cursor = db.aql.execute(aql, batch_size=200)
        edges: List[Dict[str, Any]] = list(cursor)
    except Exception as exc:
        print(f"ERROR: Could not query ELEVATES edges from ArangoDB: {exc}")
        return False

    if not edges:
        print("FAIL: Zero ELEVATES edges found in ArangoDB — graph may be empty or unsynced.")
        return False

    print(f"Found {len(edges)} ELEVATES edge(s) to verify.\n")

    # ── Load approved bindings from SQLite manifest ──────────────────────────
    bindings = get_ground_truth_bindings(MANIFEST_PATH)
    # Hard gate: the manifest must be readable and contain at least one APPROVED
    # binding.  An empty result means the manifest is missing, unreadable, or
    # has no approved entries — all of which are real failures, not skip conditions.
    if not bindings:
        print(
            f"FAIL: No APPROVED bindings could be loaded from {MANIFEST_PATH}\n"
            "Ensure reviewer_manifest.json exists and contains at least one entry "
            "with validation_status = 'APPROVED'."
        )
        return False

    # Build anchor → {binding_key, file_path} mapping (first approved match wins)
    # concept_anchor values in the manifest are plain tokens (e.g. "OEEOPERATIONAL")
    approved_anchors: Dict[str, Dict[str, str]] = {}
    for b in bindings:
        anchor = (b.get("concept_anchor") or "").upper().strip()
        if anchor and anchor not in approved_anchors:
            approved_anchors[anchor] = {
                "binding_key": b["binding_key"],
                "file_path": b.get("file_path", ""),
            }

    # ── Print header ─────────────────────────────────────────────────────────
    col_w = [28, 28, 7, 7, 55]
    header = (
        f"{'Subject (Intent)':<{col_w[0]}} "
        f"{'Object (Concept)':<{col_w[1]}} "
        f"{'Weight':>{col_w[2]}} "
        f"{'Result':<{col_w[3]}} "
        f"{'SQL Snippet Path / Note':<{col_w[4]}}"
    )
    print(header)
    print(_hr())

    pass_count = 0
    fail_count = 0
    rows_checked = 0
    skip_count = 0

    for edge in edges:
        intent_label = edge.get("intent_name") or edge.get("intent_key") or ""
        concept_label = edge.get("concept_name") or edge.get("concept_key") or ""

        # Skip dangling edges where the referenced vertex document is missing
        if not intent_label or not concept_label:
            skip_count += 1
            continue

        weight = edge.get("weight", "?")

        # Normalise: strip any "concept::" prefix that may appear in the key
        # before uppercasing so the token matches manifest concept_anchor values.
        concept_raw = concept_label
        if concept_raw.lower().startswith("concept::"):
            concept_raw = concept_raw[len("concept::"):]
        concept_anchor = concept_raw.upper().strip()

        match = approved_anchors.get(concept_anchor)

        if match:
            result = "PASS"
            note = match["file_path"] or match["binding_key"]
            pass_count += 1
        else:
            result = "FAIL"
            note = f"no APPROVED binding for anchor '{concept_anchor}'"
            fail_count += 1

        rows_checked += 1
        print(
            f"{intent_label[:col_w[0]]:<{col_w[0]}} "
            f"{concept_label[:col_w[1]]:<{col_w[1]}} "
            f"{str(weight):>{col_w[2]}} "
            f"{result:<{col_w[3]}} "
            f"{note:<{col_w[4]}}"
        )

    print(_hr())
    if skip_count:
        print(f"  (skipped {skip_count} edge(s) with missing/dangling vertex references)")
    print(f"Triples checked: {rows_checked}  |  PASS: {pass_count}  |  FAIL: {fail_count}")

    # Hard gate: at least one triple must have been verified end-to-end
    if rows_checked == 0:
        print("\nFAIL: No triples could be checked (graph may be empty or all edges are dangling).")
        return False

    if fail_count > 0:
        print(
            f"\nSweep 1 FAILED — {fail_count}/{rows_checked} triple(s) have no APPROVED binding.\n"
            "Add an approved SQL snippet for each FAIL row to the reviewer_manifest.json\n"
            "and re-run graph_sync.py to resolve."
        )
        return False

    print(f"\nSweep 1 PASSED — all {pass_count} semantic triple(s) have an APPROVED binding with a SQL snippet path.")
    return True


# ---------------------------------------------------------------------------
# Sweep 2 — AQL-to-SQLite Column Parity Matrix
# ---------------------------------------------------------------------------

def sweep2_column_parity_matrix(db, sqlite_conn: sqlite3.Connection) -> bool:
    """Fetch all column vertices from ArangoDB and check each against SQLite.

    Returns True when every column key resolves to a real SQLite column.
    Returns False (and exits non-zero) if any column is MISSING_IN_SQLITE.
    """
    from metadata_query_templates import get_column_info

    print()
    print(_hr("="))
    print("SWEEP 2 — AQL-to-SQLite Column Parity Matrix")
    print(_hr("="))

    # ── Fetch all column vertex documents from ArangoDB ──────────────────────
    try:
        aql = """
        FOR c IN columns
            RETURN {
                key         : c._key,
                table_name  : c.table_name,
                column_name : c.column_name,
                column_type : c.column_type,
                notnull     : c.notnull,
                primary_key : c.primary_key
            }
        """
        cursor = db.aql.execute(aql, batch_size=500)
        col_docs: List[Dict[str, Any]] = list(cursor)
    except Exception as exc:
        print(f"ERROR: Could not query 'columns' collection from ArangoDB: {exc}")
        return False

    if not col_docs:
        print("WARN: No column vertices found in ArangoDB — 'contains' edges may not have been synced.")
        print("Sweep 2 SKIPPED (no data).")
        return True

    print(f"Found {len(col_docs)} column vertex/vertices to check.\n")

    # ── Cache per-table PRAGMA results to avoid redundant queries ────────────
    pragma_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _get_pragma(table: str) -> Dict[str, Dict[str, Any]]:
        key = table.upper()
        if key not in pragma_cache:
            rows = get_column_info(sqlite_conn, table)
            pragma_cache[key] = {r["column_name"].upper(): r for r in rows}
        return pragma_cache[key]

    # ── Print header ─────────────────────────────────────────────────────────
    col_w = [45, 12, 5, 8, 16]
    header = (
        f"{'ArangoDB Key':<{col_w[0]}} "
        f"{'data_type':<{col_w[1]}} "
        f"{'pk':<{col_w[2]}} "
        f"{'notnull':<{col_w[3]}} "
        f"{'status':<{col_w[4]}}"
    )
    print(header)
    print(_hr())

    missing_rows: List[str] = []
    match_count = 0
    type_unknown_count = 0

    for doc in sorted(col_docs, key=lambda d: d.get("key", "")):
        arango_key = doc.get("key", "")

        # Parse table / column from the _key convention: column::TABLE.COLUMN
        stripped = arango_key
        if stripped.upper().startswith("COLUMN::"):
            stripped = stripped[len("COLUMN::"):]
        if "." in stripped:
            tbl_raw, col_raw = stripped.split(".", 1)
        else:
            tbl_raw, col_raw = stripped, ""

        tbl_upper = tbl_raw.upper()
        col_upper = col_raw.upper()

        arango_type = doc.get("column_type") or ""
        arango_pk = doc.get("primary_key", False)
        arango_notnull = doc.get("notnull", False)

        pragma_cols = _get_pragma(tbl_upper)

        if col_upper not in pragma_cols:
            status = "MISSING_IN_SQLITE"
            missing_rows.append(arango_key)
            data_type_display = arango_type or "?"
            pk_display = str(arango_pk)
            notnull_display = str(arango_notnull)
        else:
            sqlite_col = pragma_cols[col_upper]
            sqlite_type = sqlite_col["data_type"] or "TEXT"

            if not arango_type:
                status = "TYPE_UNKNOWN"
                type_unknown_count += 1
            else:
                status = "MATCH"
                match_count += 1

            data_type_display = sqlite_type
            pk_display = str(sqlite_col["pk"])
            notnull_display = str(sqlite_col["notnull"])

        print(
            f"{arango_key[:col_w[0]]:<{col_w[0]}} "
            f"{data_type_display[:col_w[1]]:<{col_w[1]}} "
            f"{pk_display:<{col_w[2]}} "
            f"{notnull_display:<{col_w[3]}} "
            f"{status:<{col_w[4]}}"
        )

    print(_hr())
    print(
        f"Columns checked: {len(col_docs)}  |  "
        f"MATCH: {match_count}  |  "
        f"TYPE_UNKNOWN: {type_unknown_count}  |  "
        f"MISSING_IN_SQLITE: {len(missing_rows)}"
    )

    if missing_rows:
        print(f"\nSweep 2 FAILED — {len(missing_rows)} column key(s) not found in SQLite:")
        for mk in missing_rows:
            print(f"  {mk}")
        print(
            "\nThis means ArangoDB has column vertices that do not exist in the physical schema.\n"
            "Re-run graph_sync.py after verifying the SQLite schema is current."
        )
        return False

    print(f"\nSweep 2 PASSED — all {len(col_docs)} column keys resolve to real SQLite columns.")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-on-no-arango",
        action="store_true",
        help="Exit 0 with SKIP when ARANGO_HOST is not set (CI-friendly flag).",
    )
    parser.add_argument(
        "--allow-sweep1-gaps",
        action="store_true",
        help=(
            "ESCAPE HATCH: treat Sweep 1 coverage gaps as warnings rather than "
            "hard failures (still exits 0). The nightly graph-sync workflow runs "
            "WITHOUT this flag as of 2026-06-04, so new gaps fail the build; pass "
            "it (via the ALLOW_SWEEP1_GAPS=true repository variable in CI) only "
            "for a deliberate, temporary exception. Sweep 2 (column parity) always "
            "hard-fails regardless of this flag."
        ),
    )
    args = parser.parse_args()

    print("=" * 72)
    print("Metadata Meaning Verification — Two-Sweep Validator")
    print("=" * 72)

    # ── Guard: ArangoDB must be reachable ────────────────────────────────────
    if not _arango_available():
        if args.skip_on_no_arango:
            print("SKIP: ARANGO_HOST is not set — skipping both sweeps (--skip-on-no-arango).")
            return 0
        print("SKIP: ARANGO_HOST is not set — cannot run ArangoDB sweeps.")
        print("Set ARANGO_HOST (and ARANGO_USER / ARANGO_ROOT_PASSWORD) to enable this check.")
        return 0

    # ── Guard: SQLite DB must exist ──────────────────────────────────────────
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"ERROR: SQLite DB not found at {SQLITE_DB_PATH}")
        return 1

    # ── Connect ──────────────────────────────────────────────────────────────
    try:
        db = _connect_arango()
        print(f"ArangoDB connected:  {os.environ.get('ARANGO_HOST')} / {os.environ.get('ARANGO_DB', 'manufacturing_graph')}")
    except Exception as exc:
        if args.skip_on_no_arango:
            print(f"SKIP: ArangoDB unreachable ({exc}) — exiting 0 (--skip-on-no-arango).")
            return 0
        print(f"ERROR: Could not connect to ArangoDB: {exc}")
        return 1

    sqlite_conn = _open_sqlite()
    print(f"SQLite connected:    {SQLITE_DB_PATH}")

    try:
        sweep1_ok = sweep1_semantic_triple_benchmark(db, sqlite_conn)
        sweep2_ok = sweep2_column_parity_matrix(db, sqlite_conn)
    finally:
        sqlite_conn.close()

    sweep1_blocks = (not sweep1_ok) and (not args.allow_sweep1_gaps)

    print()
    print(_hr("="))
    print("SUMMARY")
    print(_hr("="))
    if sweep1_ok:
        sweep1_label = "PASSED"
    elif args.allow_sweep1_gaps:
        sweep1_label = "WARN  (gaps present — --allow-sweep1-gaps set)"
    else:
        sweep1_label = "FAILED"
    print(f"  Sweep 1 (Semantic Triple Benchmark): {sweep1_label}")
    print(f"  Sweep 2 (Column Parity Matrix):      {'PASSED' if sweep2_ok else 'FAILED'}")

    if not sweep1_ok and args.allow_sweep1_gaps:
        print(
            "\nNOTE: Sweep 1 has unbound concept anchors — add approved SQL snippets "
            "to reviewer_manifest.json to resolve."
        )

    if sweep2_ok and not sweep1_blocks:
        print("\nAll blocking sweeps PASSED.")
        return 0
    else:
        print("\nOne or more blocking sweeps FAILED — see output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
