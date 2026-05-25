"""
test_bridge_collection_health.py
=================================
Two test groups in this file:

1. Unit tests for ``run_bridge_health_check_impl`` (bridge_health.py)
   ---------------------------------------------------------------
   These tests use dependency-injection seams so they run without a real
   SQLite DB or ArangoDB instance.  They cover:

   - IN SYNC        — ArangoDB counts equal SQLite counts → "✅  IN SYNC"
   - OUT OF SYNC    — counts differ                      → "❌  OUT OF SYNC"
   - MISSING COLL.  — collection absent in ArangoDB      → "❌  OUT OF SYNC"
                       (detail contains "MISSING")
   - NO ARANGO_HOST — env var not set                    → "⚠️  SKIP — ARANGO_HOST not set"
   - ARANGO CONN ERR— factory raises                     → "⚠️  SKIP — ArangoDB connection failed"

2. Integration test (existing)
   ---------------------------
   Skipped when ARANGO_HOST is not set.
   Writes a machine-readable drift report to DRIFT_REPORT_PATH on failure.

Run directly:
    python hf-space-inventory-sqlgen/tests/test_bridge_collection_health.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)

from bridge_health import BRIDGE_HEALTH_MAP, run_bridge_health_check_impl

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


# ---------------------------------------------------------------------------
# Unit tests for run_bridge_health_check_impl (no real DB or ArangoDB needed)
# ---------------------------------------------------------------------------

_SMALL_BRIDGE_MAP = {
    "Perspective_Intents": "schema_intent_perspectives",
    "Perspective_Concepts": "schema_perspective_concepts",
}

_FAKE_DB_PATH = "/fake/manufacturing.db"


def _make_sqlite_conn(counts: dict):
    """Return a fake sqlite3 connection whose execute().fetchone() returns counts."""
    class _Cursor:
        def __init__(self, table):
            self._table = table

        def fetchone(self):
            for tbl, n in counts.items():
                if tbl in self._table:
                    return (n,)
            return (0,)

    class _Conn:
        def execute(self, sql, *_):
            return _Cursor(sql)

        def close(self):
            pass

    return _Conn()


def _make_arango_db(collection_counts: dict):
    """Return a fake ArangoDB db object with has_collection / collection.count()."""
    class _Coll:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    class _DB:
        def has_collection(self, name):
            return name in collection_counts

        def collection(self, name):
            return _Coll(collection_counts[name])

    return _DB()


def test_bridge_health_in_sync() -> None:
    """When ArangoDB and SQLite counts match, status is IN SYNC."""
    sqlite_counts = {
        "schema_intent_perspectives": 10,
        "schema_perspective_concepts": 5,
    }
    arango_counts = {
        "Perspective_Intents": 10,
        "Perspective_Concepts": 5,
    }

    overall, timestamp, detail = run_bridge_health_check_impl(
        _FAKE_DB_PATH,
        _SMALL_BRIDGE_MAP,
        _os_path_exists=lambda _: True,
        _sqlite_connect=lambda _: _make_sqlite_conn(sqlite_counts),
        _arango_env_getter=lambda key: "http://localhost:8529" if key == "ARANGO_HOST" else None,
        _arango_factory=lambda: _make_arango_db(arango_counts),
    )

    assert "IN SYNC" in overall, f"Expected IN SYNC, got: {overall!r}"
    assert "✅" in overall
    assert "✅" in detail
    print(f"PASS: test_bridge_health_in_sync — {overall!r}")


def test_bridge_health_out_of_sync() -> None:
    """When ArangoDB and SQLite counts differ, status is OUT OF SYNC."""
    sqlite_counts = {
        "schema_intent_perspectives": 10,
        "schema_perspective_concepts": 5,
    }
    arango_counts = {
        "Perspective_Intents": 7,
        "Perspective_Concepts": 3,
    }

    overall, timestamp, detail = run_bridge_health_check_impl(
        _FAKE_DB_PATH,
        _SMALL_BRIDGE_MAP,
        _os_path_exists=lambda _: True,
        _sqlite_connect=lambda _: _make_sqlite_conn(sqlite_counts),
        _arango_env_getter=lambda key: "http://localhost:8529" if key == "ARANGO_HOST" else None,
        _arango_factory=lambda: _make_arango_db(arango_counts),
    )

    assert "OUT OF SYNC" in overall, f"Expected OUT OF SYNC, got: {overall!r}"
    assert "❌" in overall
    assert "❌" in detail
    print(f"PASS: test_bridge_health_out_of_sync — {overall!r}")


def test_bridge_health_missing_collection() -> None:
    """When an ArangoDB collection is absent, status is OUT OF SYNC and detail says MISSING."""
    sqlite_counts = {
        "schema_intent_perspectives": 10,
        "schema_perspective_concepts": 5,
    }
    arango_counts: dict = {}

    overall, timestamp, detail = run_bridge_health_check_impl(
        _FAKE_DB_PATH,
        _SMALL_BRIDGE_MAP,
        _os_path_exists=lambda _: True,
        _sqlite_connect=lambda _: _make_sqlite_conn(sqlite_counts),
        _arango_env_getter=lambda key: "http://localhost:8529" if key == "ARANGO_HOST" else None,
        _arango_factory=lambda: _make_arango_db(arango_counts),
    )

    assert "OUT OF SYNC" in overall, f"Expected OUT OF SYNC, got: {overall!r}"
    assert "MISSING" in detail, f"Expected MISSING in detail, got:\n{detail}"
    print(f"PASS: test_bridge_health_missing_collection — {overall!r}")


def test_bridge_health_arango_host_not_set() -> None:
    """When ARANGO_HOST is not set, status reports SKIP with clear message."""
    sqlite_counts = {
        "schema_intent_perspectives": 8,
        "schema_perspective_concepts": 4,
    }

    overall, timestamp, detail = run_bridge_health_check_impl(
        _FAKE_DB_PATH,
        _SMALL_BRIDGE_MAP,
        _os_path_exists=lambda _: True,
        _sqlite_connect=lambda _: _make_sqlite_conn(sqlite_counts),
        _arango_env_getter=lambda key: None,
    )

    assert "ARANGO_HOST not set" in overall, f"Expected ARANGO_HOST not set, got: {overall!r}"
    assert "⚠️" in overall
    assert "ARANGO_HOST" in detail
    assert "N/A" in detail
    print(f"PASS: test_bridge_health_arango_host_not_set — {overall!r}")


def test_bridge_health_arango_connection_failed() -> None:
    """When ArangoDB factory raises, status reports the connection failure."""
    sqlite_counts = {
        "schema_intent_perspectives": 3,
        "schema_perspective_concepts": 2,
    }

    def _bad_factory():
        raise RuntimeError("connection refused")

    overall, timestamp, detail = run_bridge_health_check_impl(
        _FAKE_DB_PATH,
        _SMALL_BRIDGE_MAP,
        _os_path_exists=lambda _: True,
        _sqlite_connect=lambda _: _make_sqlite_conn(sqlite_counts),
        _arango_env_getter=lambda key: "http://localhost:8529" if key == "ARANGO_HOST" else None,
        _arango_factory=_bad_factory,
    )

    assert "ArangoDB connection failed" in overall, f"Expected connection failed, got: {overall!r}"
    assert "⚠️" in overall
    assert "connection refused" in detail
    print(f"PASS: test_bridge_health_arango_connection_failed — {overall!r}")


# ---------------------------------------------------------------------------
# Integration test (existing — skipped when ARANGO_HOST not set)
# ---------------------------------------------------------------------------


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
    tests = [
        test_bridge_health_in_sync,
        test_bridge_health_out_of_sync,
        test_bridge_health_missing_collection,
        test_bridge_health_arango_host_not_set,
        test_bridge_health_arango_connection_failed,
        test_bridge_collection_counts_match,
    ]
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
