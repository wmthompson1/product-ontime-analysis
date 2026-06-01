"""Tests for sync_db_to_dab_config.sync().

Creates an in-memory / temp-file setup so no live database is required.

Coverage:
- Certified rows (certified=1, matching source_database) are merged into
  dab_config.json.
- Uncertified rows (certified=0) are ignored.
- Rows from a different source_database are ignored.
- The "note" field in the output JSON is set to the generated-from-SQLite string.
- Re-running sync() against an unchanged DB produces no diff (idempotency).

Run:
    python hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py
"""

from __future__ import annotations

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

import sync_db_to_dab_config as sut

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SOURCE_DB = "test_manufacturing"

_MINIMAL_DAB_CONFIG = {
    "entities": {
        "Customer": {
            "source": "dbo.CUSTOMER",
            "fields": {
                "CustomerId": {"description": ""},
                "CustomerName": {"description": ""},
            },
        },
        "Order": {
            "source": "crm.ORDER",
            "fields": {
                "OrderId": {"description": ""},
                "Amount": {"description": "old description"},
            },
        },
    }
}


def _make_sqlite_db(rows: list[dict]) -> str:
    """Write a temp SQLite file with dab_field_definitions populated from *rows*.

    Each dict in *rows* must supply:
        source_database, schema_name, table_name, column_name,
        field_definition, certified  (1 or 0)
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE dab_field_definitions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            source_database  TEXT,
            schema_name      TEXT,
            table_name       TEXT,
            column_name      TEXT,
            field_definition TEXT,
            certified        INTEGER DEFAULT 0
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO dab_field_definitions
            (source_database, schema_name, table_name, column_name, field_definition, certified)
        VALUES
            (:source_database, :schema_name, :table_name, :column_name, :field_definition, :certified)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


def _make_dab_config(data: dict) -> str:
    """Write *data* as JSON to a temp file and return the path."""
    fd, cfg_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return cfg_path


def _run_sync(db_path: str, cfg_path: str, source_db: str = _SOURCE_DB, dry_run: bool = False) -> None:
    """Invoke sut.sync() with module-level globals patched to temp paths."""
    with (
        mock.patch.object(sut, "SQLITE_DB_PATH", db_path),
        mock.patch.object(sut, "DAB_CONFIG_PATH", cfg_path),
        mock.patch.object(sut, "SQL_MCP_SOURCE_DATABASE", source_db),
    ):
        sut.sync(dry_run=dry_run)


def _load_cfg(cfg_path: str) -> dict:
    with open(cfg_path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_certified_rows_merged():
    """A certified=1 row that matches an entity/field updates the description."""
    import copy

    config = copy.deepcopy(_MINIMAL_DAB_CONFIG)
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "CUSTOMER",
                "column_name": "CustomerName",
                "field_definition": "Full legal name of the customer.",
                "certified": 1,
            }
        ]
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        result = _load_cfg(cfg_path)
        desc = result["entities"]["Customer"]["fields"]["CustomerName"]["description"]
        assert desc == "Full legal name of the customer.", (
            f"Expected field description to be updated. Got: {desc!r}"
        )
        print("PASS: certified rows merged into dab_config.json")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_uncertified_rows_ignored():
    """A certified=0 row must not change any field description."""
    import copy

    config = copy.deepcopy(_MINIMAL_DAB_CONFIG)
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "ORDER",
                "column_name": "Amount",
                "field_definition": "This should NOT appear.",
                "certified": 0,
            }
        ]
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        result = _load_cfg(cfg_path)
        desc = result["entities"]["Order"]["fields"]["Amount"]["description"]
        assert desc == "old description", (
            f"Uncertified row must not overwrite description. Got: {desc!r}"
        )
        print("PASS: uncertified rows ignored")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_different_source_database_ignored():
    """A row whose source_database does not match SQL_MCP_SOURCE_DATABASE is ignored."""
    import copy

    config = copy.deepcopy(_MINIMAL_DAB_CONFIG)
    db_path = _make_sqlite_db(
        [
            {
                "source_database": "other_db",
                "schema_name": "dbo",
                "table_name": "ORDER",
                "column_name": "Amount",
                "field_definition": "Should be ignored.",
                "certified": 1,
            }
        ]
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path, source_db=_SOURCE_DB)
        result = _load_cfg(cfg_path)
        desc = result["entities"]["Order"]["fields"]["Amount"]["description"]
        assert desc == "old description", (
            f"Row from different source_database must be ignored. Got: {desc!r}"
        )
        print("PASS: rows from a different source_database are ignored")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_note_field_updated():
    """After a successful sync, the 'note' key in dab_config.json must be the
    generated-from-SQLite sentinel string."""
    import copy

    config = copy.deepcopy(_MINIMAL_DAB_CONFIG)
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "CUSTOMER",
                "column_name": "CustomerId",
                "field_definition": "Primary key.",
                "certified": 1,
            }
        ]
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        result = _load_cfg(cfg_path)
        note = result.get("note", "")
        assert "Generated from SQLite" in note, (
            f"'note' field must contain 'Generated from SQLite'. Got: {note!r}"
        )
        assert "sync_db_to_dab_config" in note, (
            f"'note' field must mention the sync script. Got: {note!r}"
        )
        print("PASS: 'note' field updated to generated-from-SQLite string")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_idempotency():
    """Running sync() twice against an unchanged database produces no diff."""
    import copy

    config = copy.deepcopy(_MINIMAL_DAB_CONFIG)
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "CUSTOMER",
                "column_name": "CustomerName",
                "field_definition": "Idempotency test value.",
                "certified": 1,
            }
        ]
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        result_first = _load_cfg(cfg_path)
        json_first = json.dumps(result_first, sort_keys=True)

        _run_sync(db_path, cfg_path)
        result_second = _load_cfg(cfg_path)
        json_second = json.dumps(result_second, sort_keys=True)

        assert json_first == json_second, (
            "Re-running sync() must produce no diff in dab_config.json. "
            f"First run length: {len(json_first)}, "
            f"second run length: {len(json_second)}"
        )
        print("PASS: sync() is idempotent — second run produces no diff")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_certified_rows_merged,
        test_uncertified_rows_ignored,
        test_different_source_database_ignored,
        test_note_field_updated,
        test_idempotency,
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
    print(
        f"{'PASS' if failed == 0 else 'FAIL'}: "
        f"{len(tests) - failed}/{len(tests)} tests passed"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
