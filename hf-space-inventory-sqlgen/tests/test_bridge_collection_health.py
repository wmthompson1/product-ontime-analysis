"""
test_bridge_collection_health.py
=================================
Health check: verifies that ArangoDB bridge collection document counts match
the SQLite source-of-truth row counts after graph_sync.py has run.

Assertions
----------
  ArangoDB Perspective_Intents  document count
    == SQLite schema_intent_perspectives row count

  ArangoDB Perspective_Concepts document count
    == SQLite schema_perspective_concepts row count

A mismatch means graph_sync.py left ArangoDB in a partially-synced state;
this check surfaces that condition immediately rather than letting bad query
results propagate silently.

Behaviour
---------
- Skipped (SKIP + non-failure) when ARANGO_HOST is not set, so the suite stays
  green in offline / CI-without-ArangoDB environments.
- Fails with a non-zero exit code and a clear diagnostic message if the counts
  diverge or if the bridge collections are absent.
- Writes a machine-readable drift report to DRIFT_REPORT_PATH (default:
  drift_report.txt in the repo root) so CI notification steps can include
  the specific collection names and delta counts in alert messages.

Run directly:
    python hf-space-inventory-sqlgen/tests/test_bridge_collection_health.py

Or via the existing test runner:
    python hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py
"""

from __future__ import annotations

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)

SQLITE_DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

BRIDGE_MAP = {
    "Perspective_Intents": "schema_intent_perspectives",
    "Perspective_Concepts": "schema_perspective_concepts",
}

DRIFT_REPORT_PATH = os.environ.get(
    "DRIFT_REPORT_PATH",
    os.path.join(REPO_ROOT, "drift_report.txt"),
)


def _sqlite_counts(db_path: str) -> dict[str, int]:
    """Return {sqlite_table: row_count} for both bridge source tables."""
    conn = sqlite3.connect(db_path)
    counts: dict[str, int] = {}
    try:
        for table in BRIDGE_MAP.values():
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = row[0] if row else 0
    finally:
        conn.close()
    return counts


def _arango_counts(db) -> dict[str, int]:
    """Return {arango_collection: document_count} for both bridge collections."""
    counts: dict[str, int] = {}
    for coll_name in BRIDGE_MAP:
        if db.has_collection(coll_name):
            counts[coll_name] = db.collection(coll_name).count()
        else:
            counts[coll_name] = -1
    return counts


def _write_drift_report(lines: list[str]) -> None:
    """Write drift details to DRIFT_REPORT_PATH for CI notification steps."""
    try:
        report_dir = os.path.dirname(DRIFT_REPORT_PATH)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(DRIFT_REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:
        print(f"WARNING: could not write drift report to {DRIFT_REPORT_PATH}: {exc}")


def test_bridge_collection_counts_match() -> None:
    """Assert Perspective_Intents and Perspective_Concepts document counts
    equal the corresponding SQLite row counts.

    Skipped when ARANGO_HOST is not set.
    Writes a structured drift_report.txt on failure for CI notification steps.
    """
    if not os.environ.get("ARANGO_HOST"):
        print("SKIP: ARANGO_HOST not set — bridge collection health check skipped")
        return

    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SKIP: SQLite DB not found at {SQLITE_DB_PATH}")
        return

    try:
        from graph_sync import get_arango_client, get_arango_db
    except Exception as exc:
        print(f"SKIP: could not import ArangoDB helpers: {exc}")
        return

    try:
        client = get_arango_client()
        db = get_arango_db(client)
    except Exception as exc:
        print(f"SKIP: could not connect to ArangoDB: {exc}")
        return

    sqlite_counts = _sqlite_counts(SQLITE_DB_PATH)
    arango_counts = _arango_counts(db)

    failures: list[str] = []
    report_lines: list[str] = []

    for arango_coll, sqlite_table in BRIDGE_MAP.items():
        arango_n = arango_counts[arango_coll]
        sqlite_n = sqlite_counts[sqlite_table]

        if arango_n == -1:
            msg = (
                f"Collection '{arango_coll}' does not exist in ArangoDB "
                f"(expected {sqlite_n} docs from SQLite '{sqlite_table}'). "
                "Run graph_sync.py to create and populate it."
            )
            failures.append(f"  {msg}")
            report_lines.append(
                f"MISSING_COLLECTION collection={arango_coll} "
                f"sqlite_table={sqlite_table} sqlite_rows={sqlite_n}"
            )
            continue

        if arango_n != sqlite_n:
            diff = arango_n - sqlite_n
            direction = "extra" if diff > 0 else "missing"
            msg = (
                f"COUNT MISMATCH — '{arango_coll}': "
                f"ArangoDB={arango_n}, SQLite '{sqlite_table}'={sqlite_n} "
                f"({abs(diff)} {direction}). "
                "Re-run graph_sync.py to bring ArangoDB in sync."
            )
            failures.append(f"  {msg}")
            report_lines.append(
                f"COUNT_MISMATCH collection={arango_coll} "
                f"sqlite_table={sqlite_table} "
                f"arango_docs={arango_n} sqlite_rows={sqlite_n} "
                f"delta={diff} direction={direction}"
            )

    if failures:
        _write_drift_report(report_lines)

    assert not failures, (
        "Bridge collection health check FAILED:\n" + "\n".join(failures)
    )

    for arango_coll, sqlite_table in BRIDGE_MAP.items():
        print(
            f"PASS: '{arango_coll}' ({arango_counts[arango_coll]} docs) "
            f"== SQLite '{sqlite_table}' ({sqlite_counts[sqlite_table]} rows)"
        )
    print("PASS: all bridge collection counts match SQLite source data")


def main() -> int:
    tests = [test_bridge_collection_counts_match]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}:\n{exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
