"""sync_db_to_dab_config.py — export certified SQLite field definitions to dab_config.json.

Reads ``dab_field_definitions WHERE certified = 1 AND source_database = <SQL_MCP_SOURCE_DATABASE>``,
merges each ``field_definition`` value into the matching entity/field ``description`` in
``dab_config.json``, and writes the file back atomically (write-to-tmp + rename).

Also detects and removes entities in dab_config.json whose source table no longer exists in
manufacturing.db (renamed or dropped tables).  In --dry-run mode these are flagged as warnings
instead of being removed.

Re-running against an unchanged database produces no diff.

Usage:
    python sync_db_to_dab_config.py [--dry-run]

Environment variables:
    SQLITE_DB_PATH          Path to manufacturing.db  (default: ../app_schema/manufacturing.db
                            relative to the scripts/ directory)
    SQL_MCP_SOURCE_DATABASE Source database label used in dab_field_definitions
                            (default: manufacturing.db)
    DAB_CONFIG_PATH         Path to dab_config.json   (default: ../dab_config.json
                            relative to the scripts/ directory)
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Paths / env
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SPACE_DIR = os.path.dirname(_SCRIPTS_DIR)

SQLITE_DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(_SCRIPTS_DIR, "..", "app_schema", "manufacturing.db"),
)
SQL_MCP_SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
DAB_CONFIG_PATH = os.environ.get(
    "DAB_CONFIG_PATH",
    os.path.join(_SCRIPTS_DIR, "..", "dab_config.json"),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dab_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _build_entity_index(config: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """Return a mapping from lowercase table_name → (entity_key, lowercase_source_table).

    dab_config.json entity sources are like "crm.CUSTOMER" or "dbo.SUPPLIERS".
    We match on the last segment (after the dot) in a case-insensitive way.
    """
    index: Dict[str, Tuple[str, str]] = {}
    for entity_key, entity_val in config.get("entities", {}).items():
        source: str = entity_val.get("source", "")
        raw_table = source.split(".")[-1] if "." in source else source
        lower_table = raw_table.lower()
        index[lower_table] = entity_key
        index[entity_key.lower()] = entity_key
    return index


def _read_db_tables(db_path: str) -> set:
    """Return a set of lowercase table names that exist in the SQLite database."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        conn.close()
    return {row[0].lower() for row in rows}


def _read_certified_rows(
    db_path: str, source_database: str
) -> List[Dict[str, str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT source_database, schema_name, table_name, column_name, field_definition
            FROM dab_field_definitions
            WHERE certified = 1
              AND source_database = ?
            ORDER BY table_name, column_name
            """,
            (source_database,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(f"[ERROR] Could not query dab_field_definitions: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


def _find_stale_entities(
    config: Dict[str, Any], db_tables: set
) -> List[Tuple[str, str]]:
    """Return a list of (entity_key, source_table) pairs whose source table is absent from the DB.

    The entity source field is like "crm.CUSTOMER" or "dbo.SUPPLIERS".
    We extract the last segment (after the dot) and compare case-insensitively against
    the set of lowercase table names from sqlite_master.
    """
    stale: List[Tuple[str, str]] = []
    for entity_key, entity_val in config.get("entities", {}).items():
        source: str = entity_val.get("source", "")
        raw_table = source.split(".")[-1] if source else ""
        if not raw_table:
            continue
        if raw_table.lower() not in db_tables:
            stale.append((entity_key, raw_table))
    return stale


def sync(dry_run: bool = False) -> None:
    db_path = os.path.abspath(SQLITE_DB_PATH)
    cfg_path = os.path.abspath(DAB_CONFIG_PATH)

    if not os.path.exists(db_path):
        print(f"[ERROR] SQLite database not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(cfg_path):
        print(f"[ERROR] dab_config.json not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    rows = _read_certified_rows(db_path, SQL_MCP_SOURCE_DATABASE)
    print(
        f"[sync_db_to_dab_config] source_database={SQL_MCP_SOURCE_DATABASE!r}  "
        f"certified rows read: {len(rows)}"
    )

    config = _load_dab_config(cfg_path)

    # ------------------------------------------------------------------
    # Stale-entity detection: entities in dab_config.json whose source
    # table no longer exists in manufacturing.db (renamed or dropped).
    # ------------------------------------------------------------------
    db_tables = _read_db_tables(db_path)
    stale_entities = _find_stale_entities(config, db_tables)

    if stale_entities:
        if dry_run:
            print(
                f"[sync_db_to_dab_config] DRY-RUN — {len(stale_entities)} stale "
                f"entity/entities would be removed (source table absent from DB):"
            )
        else:
            print(
                f"[sync_db_to_dab_config] Removing {len(stale_entities)} stale "
                f"entity/entities (source table absent from DB):"
            )
        for entity_key, source_table in stale_entities:
            print(f"  {entity_key!r}  (source table: {source_table!r})")
            if not dry_run:
                del config["entities"][entity_key]
    else:
        print("[sync_db_to_dab_config] No stale entities detected.")

    if not rows:
        print("[sync_db_to_dab_config] Nothing to sync — no certified rows.")
        if dry_run:
            print(
                f"[sync_db_to_dab_config] DRY-RUN — would remove {len(stale_entities)} "
                f"stale entity/entities, 0 field(s) updated."
            )
            return
        # Still write the file if stale entities were found and this is a live run
        if not stale_entities:
            return

    entity_index = _build_entity_index(config)

    fields_updated = 0
    fields_not_matched = 0
    not_matched_details: List[str] = []

    for row in rows:
        table_lower = row["table_name"].lower()
        col_lower = row["column_name"].lower()
        field_def = row["field_definition"] or ""

        entity_key = entity_index.get(table_lower)
        if entity_key is None:
            fields_not_matched += 1
            not_matched_details.append(
                f"  no entity for table={row['table_name']!r}"
            )
            continue

        entity = config["entities"][entity_key]
        fields: Dict[str, Any] = entity.get("fields", {})

        matched_field_key = None
        for fk in fields:
            if fk.lower() == col_lower:
                matched_field_key = fk
                break

        if matched_field_key is None:
            fields_not_matched += 1
            not_matched_details.append(
                f"  no field {row['column_name']!r} in entity {entity_key!r}"
            )
            continue

        current_desc = fields[matched_field_key].get("description", "")
        if current_desc == field_def:
            continue

        if not dry_run:
            fields[matched_field_key]["description"] = field_def
        fields_updated += 1

    if not_matched_details:
        print("[sync_db_to_dab_config] Unmatched rows (no config entry found):")
        for detail in not_matched_details:
            print(detail)

    if dry_run:
        print(
            f"[sync_db_to_dab_config] DRY-RUN — would remove {len(stale_entities)} stale "
            f"entity/entities, update {fields_updated} field(s), "
            f"{fields_not_matched} not matched."
        )
        return

    config["note"] = (
        "Generated from SQLite dab_field_definitions (certified=1). "
        "Do not hand-edit — run sync_db_to_dab_config.py to refresh from the database."
    )

    cfg_dir = os.path.dirname(cfg_path)
    fd, tmp_path = tempfile.mkstemp(dir=cfg_dir, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, cfg_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(
        f"[sync_db_to_dab_config] Done — "
        f"stale entities removed: {len(stale_entities)}, "
        f"fields updated: {fields_updated}, "
        f"not matched: {fields_not_matched}."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync certified dab_field_definitions rows into dab_config.json."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing any files.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sync(dry_run=args.dry_run)
