"""Regression tests for self-healing SQLite init on databases created by an
older schema.

Background: a database created before ``schema_concepts`` gained the
``concept_type`` (and ``domain``) columns cannot be widened by
``CREATE TABLE IF NOT EXISTS``. The seed ``INSERT INTO schema_concepts
(concept_name, concept_type, description, domain)`` then fails, and because the
seed runs via ``executescript`` the *whole* script aborts on that first error —
so every table defined after ``schema_concepts`` is never created and the
resolve endpoints raise 500 ("no such table"). This was observed in CI as:

    Database init warning: table schema_concepts has no column named concept_type
    FAIL: test_gradio_resolve_endpoint_surfaces_explanation: Expected 200, got 500

``init_sqlite_db`` now widens the seed columns BEFORE running the seed, so the
idempotent seed runs to completion on an older database. These tests build that
exact stale shape in a temp DB and prove the self-heal.

Run: python hf-space-inventory-sqlgen/tests/test_db_init_self_heal.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


def _make_stale_db(path: str) -> None:
    """Create a database whose schema_concepts predates the concept_type/domain
    columns and which contains no other tables — reproducing the older shape that
    aborts the seed."""
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """CREATE TABLE schema_concepts (
                concept_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_name TEXT NOT NULL UNIQUE,
                description  TEXT
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def _columns(path: str, table: str) -> set:
    conn = sqlite3.connect(path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _table_exists(path: str, table: str) -> bool:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _count(path: str, table: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_init_self_heals_stale_schema_concepts():
    """init_sqlite_db must add the missing columns and let the full seed run."""
    try:
        import app as fastapi_app
    except Exception as exc:  # pragma: no cover - import guard
        print(f"SKIP: could not import app: {exc}")
        return

    tmpdir = tempfile.mkdtemp(prefix="self_heal_")
    stale_db = os.path.join(tmpdir, "manufacturing.db")
    _make_stale_db(stale_db)

    assert "concept_type" not in _columns(stale_db, "schema_concepts"), (
        "precondition: stale DB must NOT have concept_type"
    )

    orig_path = fastapi_app.SQLITE_DB_PATH
    orig_engine = fastapi_app.db_engine
    try:
        fastapi_app.SQLITE_DB_PATH = stale_db
        fastapi_app.db_engine = None
        fastapi_app.init_sqlite_db()

        cols = _columns(stale_db, "schema_concepts")
        assert "concept_type" in cols, (
            f"concept_type was not added by self-heal. Columns: {sorted(cols)}"
        )
        assert "domain" in cols, (
            f"domain was not added by self-heal. Columns: {sorted(cols)}"
        )

        # The seed must have run to completion: tables defined after
        # schema_concepts exist and are populated.
        assert _table_exists(stale_db, "schema_concept_fields"), (
            "schema_concept_fields missing — seed aborted before later tables"
        )
        assert _count(stale_db, "schema_concepts") > 0, (
            "schema_concepts has no seeded rows after self-heal"
        )

        conn = sqlite3.connect(stale_db)
        try:
            non_null = conn.execute(
                "SELECT COUNT(*) FROM schema_concepts WHERE concept_type IS NOT NULL"
            ).fetchone()[0]
        finally:
            conn.close()
        assert non_null > 0, "no concept rows carry a concept_type after self-heal"
    finally:
        fastapi_app.SQLITE_DB_PATH = orig_path
        fastapi_app.db_engine = orig_engine

    print(
        "PASS: init_sqlite_db self-heals stale schema_concepts "
        "(concept_type/domain added, full seed loaded)"
    )


def test_resolve_field_endpoint_200_on_stale_db():
    """The resolve_field endpoint must return 200 (not 500) against a DB created
    by an older schema, mirroring the CI failure exactly."""
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
    except Exception as exc:  # pragma: no cover - import guard
        print(f"SKIP: could not import app or TestClient: {exc}")
        return

    tmpdir = tempfile.mkdtemp(prefix="self_heal_ep_")
    stale_db = os.path.join(tmpdir, "manufacturing.db")
    _make_stale_db(stale_db)

    orig_path = fastapi_app.SQLITE_DB_PATH
    orig_engine = fastapi_app.db_engine
    try:
        fastapi_app.SQLITE_DB_PATH = stale_db
        fastapi_app.db_engine = None

        client = TestClient(fastapi_app.app, raise_server_exceptions=False)
        response = client.get(
            "/mcp/tools/resolve_field",
            params={
                "table_name": "stg_manufacturing_flat",
                "field_name": "ncm_cost",
                "intent_name": "defect_cost_analysis",
            },
        )
        assert response.status_code == 200, (
            f"Expected 200 on stale DB, got {response.status_code}: "
            f"{response.text[:200]}"
        )
        body = response.json()
        assert "explanation" in body, (
            f"'explanation' key missing from response. Keys: {list(body.keys())}"
        )
    finally:
        fastapi_app.SQLITE_DB_PATH = orig_path
        fastapi_app.db_engine = orig_engine

    print(
        "PASS: /mcp/tools/resolve_field returns 200 on a stale (older-schema) DB"
    )


def main() -> int:
    tests = [
        test_init_self_heals_stale_schema_concepts,
        test_resolve_field_endpoint_200_on_stale_db,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
