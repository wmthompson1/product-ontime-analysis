"""Tests for sync_masking_to_dab_config.sync().

Creates a temp-file setup so no live database is required. The masking sync is
the orthogonal twin of the description sync: it only ever touches each field's
``masking`` attribute, never ``description`` and never the top-level ``note``.

Coverage:
- Certified rows (certified=1, matching source_database) set fields[col]["masking"].
- Uncertified rows (certified=0) are ignored.
- Rows from a different source_database are ignored.
- The top-level "note" is NOT touched (orthogonal to the description sync).
- Existing "description" attributes are NOT touched.
- Re-running against an unchanged DB produces no diff (idempotency).
- A certified row for a table/field absent from config auto-creates it.
- create_missing=False leaves config entities untouched.
- Stale entities are NOT removed (that is the description sync's job).
- --dry-run does not mutate the config file.

Run:
    python hf-space-inventory-sqlgen/tests/test_sync_masking_to_dab_config.py
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import sys
import tempfile
import unittest.mock as mock

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "scripts"))

import sync_masking_to_dab_config as sut  # noqa: E402

_SOURCE_DB = "test_manufacturing"

_MINIMAL_DAB_CONFIG = {
    "note": "DO NOT TOUCH — owned by the description sync.",
    "entities": {
        "Customer": {
            "source": "dbo.CUSTOMER",
            "fields": {
                "customer_id": {"description": "PK."},
                "email": {"description": "Contact email."},
            },
        },
        "Order": {
            "source": "crm.ORDER",
            "fields": {
                "order_id": {"description": "PK."},
                "amount": {"description": "Total.", "masking": "none"},
            },
        },
    },
}


def _make_sqlite_db(rows: list) -> str:
    """Write a temp SQLite file with column_masking_policies populated from *rows*."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE column_masking_policies (
            source_database  TEXT NOT NULL,
            schema_name      TEXT NOT NULL,
            table_name       TEXT NOT NULL,
            column_name      TEXT NOT NULL,
            masking_strategy TEXT NOT NULL DEFAULT 'none',
            rationale        TEXT,
            certified        INTEGER NOT NULL DEFAULT 0,
            updated_at       TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO column_masking_policies
            (source_database, schema_name, table_name, column_name,
             masking_strategy, rationale, certified)
        VALUES
            (:source_database, :schema_name, :table_name, :column_name,
             :masking_strategy, :rationale, :certified)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


def _make_dab_config(data: dict) -> str:
    fd, cfg_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return cfg_path


def _run_sync(db_path, cfg_path, source_db=_SOURCE_DB, dry_run=False, create_missing=True):
    with (
        mock.patch.object(sut, "SQLITE_DB_PATH", db_path),
        mock.patch.object(sut, "DAB_CONFIG_PATH", cfg_path),
        mock.patch.object(sut, "SQL_MCP_SOURCE_DATABASE", source_db),
    ):
        sut.sync(dry_run=dry_run, create_missing=create_missing)


def _load_cfg(cfg_path) -> dict:
    with open(cfg_path, encoding="utf-8") as fh:
        return json.load(fh)


def _row(**kw):
    base = {
        "source_database": _SOURCE_DB,
        "schema_name": "dbo",
        "table_name": "CUSTOMER",
        "column_name": "email",
        "masking_strategy": "partial",
        "rationale": "PII.",
        "certified": 1,
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_certified_masking_merged():
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        field = result["entities"]["Customer"]["fields"]["email"]
        assert field.get("masking") == "partial", field
        print("PASS: certified masking row sets fields[col]['masking']")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_uncertified_ignored():
    db = _make_sqlite_db([_row(certified=0, masking_strategy="redact")])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        field = result["entities"]["Customer"]["fields"]["email"]
        assert "masking" not in field, f"uncertified must not set masking. Got: {field}"
        print("PASS: uncertified masking row ignored")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_different_source_database_ignored():
    db = _make_sqlite_db([_row(source_database="other_db", masking_strategy="redact")])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg, source_db=_SOURCE_DB)
        result = _load_cfg(cfg)
        field = result["entities"]["Customer"]["fields"]["email"]
        assert "masking" not in field, f"other source_database must be ignored. Got: {field}"
        print("PASS: rows from a different source_database are ignored")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_note_preserved():
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        assert result.get("note") == _MINIMAL_DAB_CONFIG["note"], (
            f"masking sync must NOT touch 'note'. Got: {result.get('note')!r}"
        )
        print("PASS: masking sync leaves top-level 'note' untouched")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_description_preserved():
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        field = result["entities"]["Customer"]["fields"]["email"]
        assert field.get("description") == "Contact email.", (
            f"masking sync must NOT touch 'description'. Got: {field}"
        )
        print("PASS: masking sync leaves field 'description' untouched")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_idempotency():
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        _run_sync(db, cfg)
        first = json.dumps(_load_cfg(cfg), sort_keys=True)
        _run_sync(db, cfg)
        second = json.dumps(_load_cfg(cfg), sort_keys=True)
        assert first == second, "re-running masking sync must produce no diff"
        print("PASS: masking sync is idempotent")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_unmatched_creates_entity_and_field():
    db = _make_sqlite_db([
        _row(table_name="employee", column_name="ssn",
             masking_strategy="hash", rationale="Government id.")
    ])
    cfg = _make_dab_config({"entities": {}})
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        ent = result["entities"].get("employee")
        assert ent is not None, f"entity must be auto-created. Got: {list(result['entities'])}"
        assert ent["fields"]["ssn"]["masking"] == "hash", ent
        print("PASS: certified unmatched masking row auto-creates entity + field")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_no_create_flag_leaves_config_unchanged():
    db = _make_sqlite_db([
        _row(table_name="employee", column_name="ssn", masking_strategy="hash")
    ])
    cfg = _make_dab_config({"entities": {}})
    try:
        _run_sync(db, cfg, create_missing=False)
        result = _load_cfg(cfg)
        assert result["entities"] == {}, f"no-create must not add entities. Got: {result['entities']}"
        print("PASS: create_missing=False leaves config entities untouched")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_stale_entities_not_removed():
    """The masking sync must NOT remove entities whose source table is gone."""
    config = {
        "entities": {
            "Ghost": {"source": "dbo.GHOST_TABLE", "fields": {}},
            "Customer": {
                "source": "dbo.CUSTOMER",
                "fields": {"email": {"description": "x"}},
            },
        }
    }
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(config)
    try:
        _run_sync(db, cfg)
        result = _load_cfg(cfg)
        assert "Ghost" in result["entities"], "masking sync must NOT remove stale entities"
        print("PASS: masking sync leaves stale entities in place")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def test_dry_run_does_not_mutate():
    db = _make_sqlite_db([_row()])
    cfg = _make_dab_config(copy.deepcopy(_MINIMAL_DAB_CONFIG))
    try:
        before = json.dumps(_load_cfg(cfg), sort_keys=True)
        _run_sync(db, cfg, dry_run=True)
        after = json.dumps(_load_cfg(cfg), sort_keys=True)
        assert before == after, "--dry-run must not mutate the config file"
        print("PASS: --dry-run does not mutate the config file")
    finally:
        os.unlink(db)
        os.unlink(cfg)


def main() -> int:
    tests = [
        test_certified_masking_merged,
        test_uncertified_ignored,
        test_different_source_database_ignored,
        test_note_preserved,
        test_description_preserved,
        test_idempotency,
        test_unmatched_creates_entity_and_field,
        test_no_create_flag_leaves_config_unchanged,
        test_stale_entities_not_removed,
        test_dry_run_does_not_mutate,
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
