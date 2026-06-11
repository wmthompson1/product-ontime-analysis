"""sync_masking_to_dab_config.py — export certified SQLite masking policies to dab_config.json.

The masking counterpart to ``sync_db_to_dab_config.py``. Reads
``column_masking_policies WHERE certified = 1 AND source_database = <SQL_MCP_SOURCE_DATABASE>``,
merges each ``masking_strategy`` value into the matching entity/field as a
``masking`` attribute in ``dab_config.json``, and writes the file back atomically
(write-to-tmp + rename).

Unlike the description sync, this script:
  - never removes stale entities (that is the description sync's job — removing
    them here too would race with it), and
  - never rewrites the top-level ``note`` (the two syncs are orthogonal and must
    not fight over it).

Both syncs are field-attribute-orthogonal: this one only touches each field's
``masking`` key, the description sync only touches ``description``. Re-running
against an unchanged database produces no diff.

Usage:
    python sync_masking_to_dab_config.py [--dry-run] [--no-create]

Environment variables:
    SQLITE_DB_PATH          Path to manufacturing.db  (default: ../app_schema/manufacturing.db
                            relative to the scripts/ directory)
    SQL_MCP_SOURCE_DATABASE Source database label used in column_masking_policies
                            (default: manufacturing)
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
from typing import Any, Dict, List

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


def _build_entity_index(config: Dict[str, Any]) -> Dict[str, str]:
    """Return a mapping from lowercase table_name → entity_key.

    dab_config.json entity sources are like "crm.CUSTOMER" or "dbo.SUPPLIERS".
    We match on the last segment (after the dot) in a case-insensitive way, and
    also index by the entity key itself.
    """
    index: Dict[str, str] = {}
    for entity_key, entity_val in config.get("entities", {}).items():
        source: str = entity_val.get("source", "")
        raw_table = source.split(".")[-1] if "." in source else source
        index[raw_table.lower()] = entity_key
        index[entity_key.lower()] = entity_key
    return index


def _read_certified_rows(
    db_path: str, source_database: str
) -> List[Dict[str, str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT source_database, schema_name, table_name, column_name,
                   masking_strategy, rationale
            FROM column_masking_policies
            WHERE certified = 1
              AND source_database = ?
            ORDER BY table_name, column_name
            """,
            (source_database,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(f"[ERROR] Could not query column_masking_policies: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


def sync(dry_run: bool = False, create_missing: bool = True) -> None:
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
        f"[sync_masking_to_dab_config] source_database={SQL_MCP_SOURCE_DATABASE!r}  "
        f"certified masking rows read: {len(rows)}"
    )

    config = _load_dab_config(cfg_path)

    if not rows:
        print("[sync_masking_to_dab_config] Nothing to sync — no certified masking rows.")
        return

    entity_index = _build_entity_index(config)

    masks_updated = 0
    masks_created = 0
    entities_created = 0
    fields_created = 0
    fields_not_matched = 0
    not_matched_details: List[str] = []

    for row in rows:
        table_lower = row["table_name"].lower()
        col_lower = row["column_name"].lower()
        strategy = row["masking_strategy"] or "none"

        entity_key = entity_index.get(table_lower)
        if entity_key is None:
            if not create_missing:
                fields_not_matched += 1
                not_matched_details.append(
                    f"  no entity for table={row['table_name']!r}"
                )
                continue
            # Auto-create an entity block so certified masking for tables not yet
            # in dab_config.json still publishes (the DAB stand-in grows with the
            # curated set). Idempotent: the next run finds it via the entity index.
            entity_key = row["table_name"]
            schema = row["schema_name"] or ""
            new_source = f"{schema}.{row['table_name']}" if schema else row["table_name"]
            if not dry_run:
                config.setdefault("entities", {})[entity_key] = {
                    "source": new_source,
                    "description": "",
                    "fields": {},
                }
            entity_index[table_lower] = entity_key
            entity_index[entity_key.lower()] = entity_key
            entities_created += 1

        entity = config.get("entities", {}).get(entity_key)
        if entity is None:
            # dry-run path for a would-be-created entity: nothing on disk yet.
            entity = {"fields": {}}
        fields: Dict[str, Any] = entity.setdefault("fields", {})

        matched_field_key = None
        for fk in fields:
            if fk.lower() == col_lower:
                matched_field_key = fk
                break

        if matched_field_key is None:
            if not create_missing:
                fields_not_matched += 1
                not_matched_details.append(
                    f"  no field {row['column_name']!r} in entity {entity_key!r}"
                )
                continue
            if not dry_run:
                fields[row["column_name"]] = {"masking": strategy}
            fields_created += 1
            masks_created += 1
            continue

        current_mask = fields[matched_field_key].get("masking")
        if current_mask == strategy:
            continue

        if not dry_run:
            if current_mask is None:
                masks_created += 1
            else:
                masks_updated += 1
            fields[matched_field_key]["masking"] = strategy
        else:
            if current_mask is None:
                masks_created += 1
            else:
                masks_updated += 1

    if not_matched_details:
        print("[sync_masking_to_dab_config] Unmatched rows (no config entry found):")
        for detail in not_matched_details:
            print(detail)

    if dry_run:
        print(
            f"[sync_masking_to_dab_config] DRY-RUN — would create "
            f"{entities_created} entity/entities, {fields_created} field(s), "
            f"set {masks_created} new mask(s), update {masks_updated} mask(s), "
            f"{fields_not_matched} not matched."
        )
        return

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
        f"[sync_masking_to_dab_config] Done — "
        f"entities created: {entities_created}, "
        f"fields created: {fields_created}, "
        f"masks set: {masks_created}, "
        f"masks updated: {masks_updated}, "
        f"not matched: {fields_not_matched}."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync certified column_masking_policies rows into dab_config.json."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing any files.",
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Only update fields that already exist in dab_config.json; do not "
             "create new entity/field blocks for certified masking rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sync(dry_run=args.dry_run, create_missing=not args.no_create)
