"""Tests for sync_db_to_dab_config.sync() and _find_stale_entities().

Creates an in-memory / temp-file setup so no live database is required.

Coverage:
- Certified rows (certified=1, matching source_database) are merged into
  dab_config.json.
- Uncertified rows (certified=0) are ignored.
- Rows from a different source_database are ignored.
- The "note" field in the output JSON is set to the generated-from-SQLite string.
- Re-running sync() against an unchanged DB produces no diff (idempotency).
- _find_stale_entities(): all tables present (no stale returned).
- _find_stale_entities(): one stale entity detected.
- _find_stale_entities(): all entities stale.
- _find_stale_entities(): entity with missing source field is skipped.
- --dry-run does not mutate the config file (stale entities stay on disk).
- Live run removes only the stale entity and leaves valid ones intact.

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


def _make_sqlite_db(rows: list[dict], extra_tables: list[str] | None = None) -> str:
    """Write a temp SQLite file with dab_field_definitions populated from *rows*.

    Each dict in *rows* must supply:
        source_database, schema_name, table_name, column_name,
        field_definition, certified  (1 or 0)

    *extra_tables* — additional table names to CREATE as empty stubs so that
    _find_stale_entities() in sync_db_to_dab_config doesn't treat the
    corresponding dab_config.json entities as stale (their source tables must
    appear in sqlite_master for the check to pass).
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
    for tbl in (extra_tables or []):
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{tbl}" (_id INTEGER PRIMARY KEY)')
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
        ],
        extra_tables=["CUSTOMER", "ORDER"],
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
        ],
        extra_tables=["CUSTOMER", "ORDER"],
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
        ],
        extra_tables=["CUSTOMER", "ORDER"],
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
        ],
        extra_tables=["CUSTOMER", "ORDER"],
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
        ],
        extra_tables=["CUSTOMER", "ORDER"],
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
# Stale-entity detection tests (_find_stale_entities)
# ---------------------------------------------------------------------------


def test_find_stale_no_stale_when_all_tables_present():
    """All entity source tables exist in the DB → empty stale list."""
    db_tables = {"customers", "orders", "products"}
    config = {
        "entities": {
            "Customer": {"source": "dbo.CUSTOMERS", "fields": {}},
            "Order":    {"source": "dbo.ORDERS",    "fields": {}},
            "Product":  {"source": "dbo.PRODUCTS",  "fields": {}},
        }
    }
    result = sut._find_stale_entities(config, db_tables)
    assert result == [], f"Expected no stale entities, got: {result}"
    print("PASS: _find_stale_entities — no stale when all tables present")


def test_find_stale_one_missing_table():
    """One entity whose source table is absent → returned in stale list."""
    db_tables = {"customers", "orders"}
    config = {
        "entities": {
            "Customer":  {"source": "dbo.CUSTOMERS",   "fields": {}},
            "Order":     {"source": "dbo.ORDERS",      "fields": {}},
            "OldLedger": {"source": "dbo.OLD_LEDGER",  "fields": {}},
        }
    }
    result = sut._find_stale_entities(config, db_tables)
    assert len(result) == 1, f"Expected 1 stale entity, got: {result}"
    entity_key, source_table = result[0]
    assert entity_key == "OldLedger", f"Expected OldLedger stale, got: {entity_key}"
    assert source_table.lower() == "old_ledger", f"Unexpected source_table: {source_table}"
    print("PASS: _find_stale_entities — one stale entity detected")


def test_find_stale_all_entities_stale():
    """All entity source tables absent → all returned as stale."""
    db_tables: set = set()
    config = {
        "entities": {
            "Alpha": {"source": "dbo.ALPHA", "fields": {}},
            "Beta":  {"source": "dbo.BETA",  "fields": {}},
        }
    }
    result = sut._find_stale_entities(config, db_tables)
    assert len(result) == 2, f"Expected 2 stale entities, got: {result}"
    keys = {r[0] for r in result}
    assert "Alpha" in keys and "Beta" in keys, f"Unexpected keys: {keys}"
    print("PASS: _find_stale_entities — all entities stale")


def test_find_stale_entity_missing_source_field():
    """Entity with no 'source' key is skipped (not flagged as stale)."""
    db_tables = {"customers"}
    config = {
        "entities": {
            "Customer": {"source": "dbo.CUSTOMERS", "fields": {}},
            "NoSource": {"fields": {}},
        }
    }
    result = sut._find_stale_entities(config, db_tables)
    assert result == [], (
        f"Entity with no 'source' must be skipped, not flagged stale. Got: {result}"
    )
    print("PASS: _find_stale_entities — entity missing source field is skipped")


# ---------------------------------------------------------------------------
# Dry-run / live-run mutation tests (integration: sync() with temp files)
# ---------------------------------------------------------------------------


def _run_sync_with_temp_files(db_tables: list, config_dict: dict, dry_run: bool) -> tuple:
    """Create temp DB + config files, call sync(), return (original_cfg, on_disk_cfg)."""
    import copy

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE dab_field_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_database TEXT, schema_name TEXT,
            table_name TEXT, column_name TEXT,
            field_definition TEXT, certified INTEGER DEFAULT 0
        )
        """
    )
    for tbl in db_tables:
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{tbl}" (_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

    fd2, cfg_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        json.dump(config_dict, fh)

    original_cfg = copy.deepcopy(config_dict)
    try:
        _run_sync(db_path, cfg_path, source_db="__no_source__", dry_run=dry_run)
        on_disk = _load_cfg(cfg_path)
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)

    return original_cfg, on_disk


def test_dry_run_does_not_remove_stale_entity():
    """--dry-run must NOT remove stale entities from the config file on disk."""
    config = {
        "entities": {
            "Ghost": {"source": "dbo.GHOST_TABLE", "fields": {}},
            "Real":  {"source": "dbo.REAL_TABLE",  "fields": {}},
        }
    }
    _, on_disk = _run_sync_with_temp_files(
        db_tables=["real_table"],
        config_dict=config,
        dry_run=True,
    )
    entities = on_disk.get("entities", {})
    assert "Ghost" in entities, "dry-run must not delete the stale entity from disk"
    assert "Real" in entities, "dry-run must keep valid entities"
    print("PASS: dry-run does not remove stale entity from config file")


def test_live_run_removes_stale_entity_only():
    """Live run must remove the stale entity and leave valid ones intact."""
    config = {
        "entities": {
            "Ghost": {"source": "dbo.GHOST_TABLE", "fields": {}},
            "Real":  {"source": "dbo.REAL_TABLE",  "fields": {}},
        }
    }
    _, on_disk = _run_sync_with_temp_files(
        db_tables=["real_table"],
        config_dict=config,
        dry_run=False,
    )
    entities = on_disk.get("entities", {})
    assert "Ghost" not in entities, "live run must delete stale entity from config"
    assert "Real" in entities, "live run must keep valid entity intact"
    print("PASS: live run removes only the stale entity, valid entity survives")


# ---------------------------------------------------------------------------
# Auto-create tests (certified rows for tables/fields not yet in dab_config.json)
# ---------------------------------------------------------------------------


def test_certified_unmatched_creates_entity_and_field():
    """A certified row for a table absent from the config creates an entity+field."""
    config = {"entities": {}}
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "work_order",
                "column_name": "status",
                "field_definition": "Shop-floor lifecycle stage of the work order.",
                "certified": 1,
            }
        ],
        extra_tables=["work_order"],
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        result = _load_cfg(cfg_path)
        ent = result["entities"].get("work_order")
        assert ent is not None, f"entity must be auto-created. Got: {list(result['entities'])}"
        desc = ent["fields"]["status"]["description"]
        assert desc == "Shop-floor lifecycle stage of the work order.", desc
        print("PASS: certified unmatched row auto-creates entity + field block")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_auto_create_is_idempotent():
    """Re-running after an auto-create produces no diff."""
    config = {"entities": {}}
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "work_order",
                "column_name": "status",
                "field_definition": "Lifecycle stage.",
                "certified": 1,
            }
        ],
        extra_tables=["work_order"],
    )
    cfg_path = _make_dab_config(config)
    try:
        _run_sync(db_path, cfg_path)
        first = json.dumps(_load_cfg(cfg_path), sort_keys=True)
        _run_sync(db_path, cfg_path)
        second = json.dumps(_load_cfg(cfg_path), sort_keys=True)
        assert first == second, "auto-create path must be idempotent"
        print("PASS: auto-create path is idempotent on re-run")
    finally:
        os.unlink(db_path)
        os.unlink(cfg_path)


def test_no_create_flag_leaves_config_unchanged():
    """With create_missing=False, an unmatched certified row is not added."""
    config = {"entities": {}}
    db_path = _make_sqlite_db(
        [
            {
                "source_database": _SOURCE_DB,
                "schema_name": "dbo",
                "table_name": "work_order",
                "column_name": "status",
                "field_definition": "Lifecycle stage.",
                "certified": 1,
            }
        ],
        extra_tables=["work_order"],
    )
    cfg_path = _make_dab_config(config)
    try:
        with (
            mock.patch.object(sut, "SQLITE_DB_PATH", db_path),
            mock.patch.object(sut, "DAB_CONFIG_PATH", cfg_path),
            mock.patch.object(sut, "SQL_MCP_SOURCE_DATABASE", _SOURCE_DB),
        ):
            sut.sync(dry_run=False, create_missing=False)
        result = _load_cfg(cfg_path)
        assert result["entities"] == {}, f"no-create must not add entities. Got: {result['entities']}"
        print("PASS: create_missing=False leaves config entities untouched")
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
        test_find_stale_no_stale_when_all_tables_present,
        test_find_stale_one_missing_table,
        test_find_stale_all_entities_stale,
        test_find_stale_entity_missing_source_field,
        test_dry_run_does_not_remove_stale_entity,
        test_live_run_removes_stale_entity_only,
        test_certified_unmatched_creates_entity_and_field,
        test_auto_create_is_idempotent,
        test_no_create_flag_leaves_config_unchanged,
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
