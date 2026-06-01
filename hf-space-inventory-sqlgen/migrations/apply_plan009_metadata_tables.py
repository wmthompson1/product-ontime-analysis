"""
migrations/apply_plan009_metadata_tables.py
-------------------------------------------
Creates the three Plan-009 app-metadata tables in manufacturing.db if they do
not already exist.  Safe to re-run (all statements use CREATE TABLE IF NOT
EXISTS guards).

Tables created:
  - dab_field_definitions      SME-approved field definition text
  - schema_topology_metadata   Containment-graph topology annotations
  - api_field_descriptions     API / DAB display names, descriptions, examples

Usage:
    python migrations/apply_plan009_metadata_tables.py [--db PATH]

Default database path: hf-space-inventory-sqlgen/app_schema/manufacturing.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = (
    Path(__file__).parent.parent / "app_schema" / "manufacturing.db"
)

DDL_STATEMENTS = [
    # ── api_field_descriptions ──────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS api_field_descriptions (
        source_database TEXT    NOT NULL,
        schema_name     TEXT    NOT NULL,
        table_name      TEXT    NOT NULL,
        column_name     TEXT    NOT NULL,
        display_name    TEXT,
        description     TEXT,
        example_value   TEXT,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (source_database, schema_name, table_name, column_name)
    )
    """,
    # ── schema_topology_metadata ────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schema_topology_metadata (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        source_node_type TEXT    NOT NULL
                         CHECK(source_node_type IN ('database', 'schema', 'table', 'column')),
        target_node_type TEXT    NOT NULL
                         CHECK(target_node_type IN ('database', 'schema', 'table', 'column')),
        source_key       TEXT    NOT NULL,
        target_key       TEXT    NOT NULL,
        edge_predicate   TEXT    NOT NULL DEFAULT 'CONTAINS',
        weight           INTEGER NOT NULL DEFAULT 1,
        notes            TEXT,
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_node_type, target_node_type, source_key, target_key, edge_predicate)
    )
    """,
    # ── dab_field_definitions ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dab_field_definitions (
        source_database  TEXT    NOT NULL,
        schema_name      TEXT    NOT NULL,
        table_name       TEXT    NOT NULL,
        column_name      TEXT    NOT NULL,
        field_definition TEXT,
        certified        INTEGER NOT NULL DEFAULT 0 CHECK(certified IN (0, 1)),
        updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (source_database, schema_name, table_name, column_name)
    )
    """,
]

TARGET_TABLES = {"api_field_descriptions", "schema_topology_metadata", "dab_field_definitions"}


def get_existing_tables(conn: sqlite3.Connection) -> set:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def run_migration(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[apply_plan009] ERROR: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        existing = get_existing_tables(conn)
        already_present = TARGET_TABLES & existing
        to_create = TARGET_TABLES - existing

        if already_present:
            print(f"[apply_plan009] Already present (skipped): {sorted(already_present)}")
        if not to_create:
            print("[apply_plan009] All three Plan-009 tables already exist — nothing to do.")
            return

        with conn:
            for ddl in DDL_STATEMENTS:
                conn.execute(ddl)

        created = get_existing_tables(conn) & to_create
        print(f"[apply_plan009] Created: {sorted(created)}")

        missing = to_create - created
        if missing:
            print(f"[apply_plan009] ERROR: failed to create: {sorted(missing)}", file=sys.stderr)
            sys.exit(1)

        print("[apply_plan009] Migration complete.")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Path to manufacturing.db (default: %(default)s)",
    )
    args = parser.parse_args()
    run_migration(args.db)


if __name__ == "__main__":
    main()
