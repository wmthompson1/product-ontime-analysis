"""Tests for masking_policy_pipeline.

Uses a temp SQLite file with a small business table plus the column_masking_policies
overlay table so no live database is required.

Coverage:
- suggest_masking_strategy() maps obvious PII names to strategies and defaults
  unknown columns to 'none'.
- suggest_masking_strategy() priority: a secret/credential name redacts before a
  generic name rule applies.
- upsert_masking_policy() is idempotent (second call -> still one row, updated)
  and never changes the certified flag (save does not un-certify).
- certify_masking_policy() writes certified=1 and persists the strategy.
- upsert rejects an unknown strategy.
- fill_missing_masking() flags only sensitive columns and skips 'none' columns.
- compute_masking_coverage() aggregates policied/certified across all tables.

Run:
    python hf-space-inventory-sqlgen/tests/test_masking_policy_pipeline.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import masking_policy_pipeline as m  # noqa: E402

_SRC_DB = "test_manufacturing"
_SCHEMA = "dbo"


def _make_db() -> str:
    """Build a temp DB: one business table, one staging table, the masking table."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE customer (
            customer_id INTEGER PRIMARY KEY,
            email       TEXT,
            phone       TEXT,
            status      TEXT
        );
        CREATE TABLE stg_raw (x TEXT);
        CREATE TABLE column_masking_policies (
            source_database  TEXT NOT NULL,
            schema_name      TEXT NOT NULL,
            table_name       TEXT NOT NULL,
            column_name      TEXT NOT NULL,
            masking_strategy TEXT NOT NULL DEFAULT 'none'
                CHECK(masking_strategy IN ('none', 'hash', 'partial', 'redact')),
            rationale        TEXT,
            certified        INTEGER NOT NULL DEFAULT 0 CHECK(certified IN (0, 1)),
            updated_at       TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        INSERT INTO customer (customer_id, email, phone, status) VALUES
            (1, 'a@x.com', '555-1000', 'OPEN'),
            (2, 'b@y.com', '555-2000', 'CLOSED');
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _row(db_path: str, table: str, column: str):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT masking_strategy, certified FROM column_masking_policies "
            "WHERE table_name=? AND column_name=?",
            (table, column),
        ).fetchone()
    finally:
        conn.close()


def _count(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_suggest_known_pii():
    assert m.suggest_masking_strategy("customer", "email")["masking_strategy"] == "partial"
    assert m.suggest_masking_strategy("customer", "phone")["masking_strategy"] == "partial"
    assert m.suggest_masking_strategy("employee", "ssn")["masking_strategy"] == "hash"
    assert m.suggest_masking_strategy("account", "account_number")["masking_strategy"] == "hash"
    assert m.suggest_masking_strategy("customer", "home_address")["masking_strategy"] == "redact"
    assert m.suggest_masking_strategy("work_order", "status")["masking_strategy"] == "none"
    print("PASS: suggest_masking_strategy maps PII names + defaults to none")


def test_suggest_no_domain_false_positives():
    # Manufacturing 'routing' (shop-floor routing) must NOT be flagged as a
    # financial routing number; the hash rule keys on routing_number/routing_no.
    assert m.suggest_masking_strategy("work_order", "routing_template")["masking_strategy"] == "none"
    assert m.suggest_masking_strategy("work_order", "routing_id")["masking_strategy"] == "none"
    # But a real bank routing number still hashes.
    assert m.suggest_masking_strategy("payment", "routing_number")["masking_strategy"] == "hash"
    print("PASS: suggest_masking_strategy avoids manufacturing 'routing' false positive")


def test_suggest_priority_secret_before_name():
    # "user_password" contains neither a name keyword nor anything but the
    # credential rule -> redact wins (highest priority rule).
    d = m.suggest_masking_strategy("login", "user_password")
    assert d["masking_strategy"] == "redact", d
    assert d["_source"] == "deterministic"
    print("PASS: suggest_masking_strategy applies highest-priority rule first")


def test_upsert_idempotent_and_preserves_certified():
    db = _make_db()
    try:
        r1 = m.upsert_masking_policy(
            "customer", "email", "partial", "first",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r1["ok"], r1
        assert _count(db, "column_masking_policies") == 1
        # Certify it, then re-save (save must NOT un-certify).
        m.certify_masking_policy(
            "customer", "email", "partial", "first", certified=True,
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert _row(db, "customer", "email")[1] == 1, "certify must set certified=1"
        r2 = m.upsert_masking_policy(
            "customer", "email", "hash", "second",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r2["ok"], r2
        assert _count(db, "column_masking_policies") == 1, "upsert must not duplicate"
        strat, cert = _row(db, "customer", "email")
        assert strat == "hash", f"second upsert must overwrite strategy, got {strat!r}"
        assert cert == 1, "save must preserve certified flag"
        print("PASS: upsert is idempotent, overwrites strategy, preserves certified")
    finally:
        os.unlink(db)


def test_certify_writes_flag():
    db = _make_db()
    try:
        res = m.certify_masking_policy(
            "customer", "phone", "partial", "Contact PII.", certified=True,
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert res["ok"], res
        strat, cert = _row(db, "customer", "phone")
        assert strat == "partial", strat
        assert cert == 1, "certified flag must be 1"
        print("PASS: certify_masking_policy writes certified=1")
    finally:
        os.unlink(db)


def test_upsert_rejects_unknown_strategy():
    db = _make_db()
    try:
        res = m.upsert_masking_policy(
            "customer", "email", "scramble", "bad",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert not res["ok"], "unknown strategy must be rejected"
        assert _count(db, "column_masking_policies") == 0
        print("PASS: upsert rejects an unknown strategy")
    finally:
        os.unlink(db)


def test_fill_missing_flags_only_sensitive():
    db = _make_db()
    try:
        flagged = m.fill_missing_masking(
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        # customer has email + phone (sensitive) -> 2 flagged; status + id -> none.
        assert flagged == 2, f"expected 2 flagged, got {flagged}"
        assert _row(db, "customer", "email") is not None
        assert _row(db, "customer", "status") is None, "non-sensitive must stay unpolicied"
        # Idempotent: re-run flags nothing new.
        again = m.fill_missing_masking(
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert again == 0, f"re-run must flag 0, got {again}"
        print("PASS: fill_missing_masking flags only sensitive columns, idempotent")
    finally:
        os.unlink(db)


def test_compute_masking_coverage_overall():
    schema = {
        "customer": {
            "id": {"masking_strategy": "none", "masking_certified": 0},
            "email": {"masking_strategy": "partial", "masking_certified": 1},
            "notes": {},  # no policy row -> not policied
        },
        "supplier": {
            "id": {"masking_strategy": "hash", "masking_certified": 1},
            "name": {},
        },
        "empty_table": {},
    }
    cov = m.compute_masking_coverage(schema)
    assert cov["tables"] == 3, cov
    assert cov["columns"] == 5, cov
    assert cov["policied"] == 3, cov
    assert cov["certified"] == 2, cov
    empty = m.compute_masking_coverage({})
    assert empty == {"tables": 0, "columns": 0, "policied": 0, "certified": 0}
    print("PASS: compute_masking_coverage aggregates overall coverage correctly")


def main() -> int:
    tests = [
        test_suggest_known_pii,
        test_suggest_no_domain_false_positives,
        test_suggest_priority_secret_before_name,
        test_upsert_idempotent_and_preserves_certified,
        test_certify_writes_flag,
        test_upsert_rejects_unknown_strategy,
        test_fill_missing_flags_only_sensitive,
        test_compute_masking_coverage_overall,
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
