"""Tests for field_description_pipeline.

Uses a temp SQLite file with a small business table plus the two overlay tables
(api_field_descriptions, dab_field_definitions) so no live database is required.

Coverage:
- humanize() expands snake_case + known abbreviations.
- deterministic_draft() returns display_name / description / example_value and
  flags a bounded column as categorical.
- upsert_field_description() is idempotent (second call -> still one row, updated).
- certify_field_definition() writes certified=1 into dab_field_definitions.
- list_business_columns() excludes metadata + staging tables.
- fill_missing() drafts only undescribed columns and preserves existing ones.

Run:
    python hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import field_description_pipeline as p  # noqa: E402

_SRC_DB = "test_manufacturing"
_SCHEMA = "dbo"


def _make_db() -> str:
    """Build a temp DB: one business table, one staging table, two overlay tables."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE work_order (
            work_order_id INTEGER PRIMARY KEY,
            status        TEXT,
            quantity      INTEGER
        );
        CREATE TABLE stg_raw (x TEXT);
        CREATE TABLE api_field_descriptions (
            source_database TEXT, schema_name TEXT,
            table_name TEXT, column_name TEXT,
            display_name TEXT, description TEXT, example_value TEXT,
            updated_at TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        CREATE TABLE dab_field_definitions (
            source_database TEXT, schema_name TEXT,
            table_name TEXT, column_name TEXT,
            field_definition TEXT, certified INTEGER DEFAULT 0,
            updated_at TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        INSERT INTO work_order (work_order_id, status, quantity) VALUES
            (1, 'OPEN', 10), (2, 'CLOSED', 5), (3, 'OPEN', 7), (4, 'RELEASED', 1);
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _row_count(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_humanize():
    assert p.humanize("three_way_match_status") == "Three Way Match Status"
    assert p.humanize("order_qty") == "Order Quantity"
    assert p.humanize("customer_id") == "Customer ID"
    print("PASS: humanize expands snake_case + abbreviations")


def test_deterministic_draft_categorical():
    db = _make_db()
    try:
        d = p.deterministic_draft("work_order", "status", db_path=db)
        assert d["display_name"] == "Status", d
        assert d["_source"] == "deterministic"
        assert d["example_value"] in {"OPEN", "CLOSED", "RELEASED"}, d
        assert "categorical" in d["description"].lower(), d["description"]
        print("PASS: deterministic_draft flags a bounded column as categorical")
    finally:
        os.unlink(db)


def test_deterministic_draft_pk():
    db = _make_db()
    try:
        d = p.deterministic_draft("work_order", "work_order_id", db_path=db)
        assert "primary key" in d["description"].lower(), d["description"]
        print("PASS: deterministic_draft describes a PK column")
    finally:
        os.unlink(db)


def test_upsert_idempotent():
    db = _make_db()
    try:
        r1 = p.upsert_field_description(
            "work_order", "status", "Work Order Status", "first", "OPEN",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r1["ok"], r1
        assert _row_count(db, "api_field_descriptions") == 1
        r2 = p.upsert_field_description(
            "work_order", "status", "Work Order Status", "second", "CLOSED",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r2["ok"], r2
        assert _row_count(db, "api_field_descriptions") == 1, "upsert must not duplicate"
        conn = sqlite3.connect(db)
        desc = conn.execute(
            "SELECT description FROM api_field_descriptions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()[0]
        conn.close()
        assert desc == "second", f"second upsert must overwrite, got {desc!r}"
        print("PASS: upsert_field_description is idempotent and updates in place")
    finally:
        os.unlink(db)


def test_certify_writes_dab():
    db = _make_db()
    try:
        res = p.certify_field_definition(
            "work_order", "status", "Shop-floor lifecycle stage.", certified=True,
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert res["ok"], res
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT field_definition, certified FROM dab_field_definitions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()
        conn.close()
        assert row is not None, "certify must insert a dab_field_definitions row"
        assert row[0] == "Shop-floor lifecycle stage.", row
        assert row[1] == 1, "certified flag must be 1"
        print("PASS: certify_field_definition writes certified=1 to dab_field_definitions")
    finally:
        os.unlink(db)


def test_list_business_columns_excludes_metadata_and_staging():
    db = _make_db()
    try:
        cols = p.list_business_columns(db_path=db)
        tables = {t for t, _ in cols}
        assert "work_order" in tables, tables
        assert "stg_raw" not in tables, "staging tables must be excluded"
        assert "api_field_descriptions" not in tables, "metadata tables must be excluded"
        assert "dab_field_definitions" not in tables, "metadata tables must be excluded"
        print("PASS: list_business_columns excludes metadata + staging tables")
    finally:
        os.unlink(db)


def test_fill_missing_preserves_existing():
    db = _make_db()
    try:
        # Pre-seed one column with a curated value.
        p.upsert_field_description(
            "work_order", "status", "Curated Status", "DO NOT OVERWRITE", "OPEN",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        filled = p.fill_missing(
            db_path=db, use_ai=False,
            source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        # work_order has 3 columns; status pre-seeded -> 2 newly drafted.
        assert filled == 2, f"expected 2 newly drafted, got {filled}"
        conn = sqlite3.connect(db)
        preserved = conn.execute(
            "SELECT description FROM api_field_descriptions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()[0]
        conn.close()
        assert preserved == "DO NOT OVERWRITE", f"curated row must be preserved, got {preserved!r}"
        print("PASS: fill_missing drafts only gaps and preserves existing rows")
    finally:
        os.unlink(db)


def main() -> int:
    tests = [
        test_humanize,
        test_deterministic_draft_categorical,
        test_deterministic_draft_pk,
        test_upsert_idempotent,
        test_certify_writes_dab,
        test_list_business_columns_excludes_metadata_and_staging,
        test_fill_missing_preserves_existing,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
