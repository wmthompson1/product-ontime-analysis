"""
migrations/add_sql_graph_tables.py
----------------------------------
Creates the two SQL graph source tables in manufacturing.db if they do not
already exist.  Safe to re-run (CREATE TABLE IF NOT EXISTS guards).

These tables hold the full canonical graph (nodes + edges in the fixed 6-slot
composite-key form) that replit_integrations/export_graph_metadata.py
materializes and then serializes graph_metadata.json FROM.  SQLite is the source
of truth; the JSON is provably a dump of these rows.

Tables created:
  - sql_graph_nodes           table + column + concept nodes (one column per JSON node field)
  - sql_graph_edges           has_column + references + resolves_to edges
  - sql_graph_authored_edges  durable SME-authored edges (Define Relationship UI)
                              that the exporter merges into sql_graph_edges

Usage:
    python migrations/add_sql_graph_tables.py [--db PATH]

Default database path: hf-space-inventory-sqlgen/app_schema/manufacturing.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent / "app_schema" / "manufacturing.db"

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS sql_graph_nodes (
        ordinal       INTEGER NOT NULL,
        _key          TEXT    NOT NULL PRIMARY KEY,
        _id           TEXT    NOT NULL,
        node_type     TEXT    NOT NULL CHECK(node_type IN ('table', 'column', 'concept')),
        node_family   TEXT    NOT NULL,
        perspective   TEXT    NOT NULL,
        table_name    TEXT,
        column_name   TEXT,
        column_slot   TEXT,
        concept_name  TEXT,
        concept_type  TEXT,
        domain        TEXT,
        synonyms      TEXT,
        tags          TEXT,
        predicate     TEXT    NOT NULL,
        unique_id     TEXT    NOT NULL,
        description   TEXT,
        column_type   TEXT,
        "notnull"     INTEGER,
        default_value TEXT,
        primary_key   INTEGER,
        foreign_key   INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sql_graph_edges (
        ordinal           INTEGER NOT NULL,
        _key              TEXT    NOT NULL PRIMARY KEY,
        _id               TEXT    NOT NULL,
        _from             TEXT    NOT NULL,
        _to               TEXT    NOT NULL,
        edge_family       TEXT    NOT NULL,
        edge_type         TEXT    NOT NULL CHECK(edge_type IN ('has_column', 'references', 'resolves_to')),
        perspective       TEXT    NOT NULL,
        unique_id         TEXT    NOT NULL,
        references_table  TEXT,
        references_column TEXT,
        weight            INTEGER,
        priority_weight   INTEGER,
        field_component   INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sql_graph_authored_edges (
        authored_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        edge_type     TEXT    NOT NULL CHECK(edge_type IN ('has_column', 'references', 'resolves_to')),
        from_table    TEXT    NOT NULL,
        from_column   TEXT    NOT NULL DEFAULT '',
        to_table      TEXT    NOT NULL,
        to_column     TEXT    NOT NULL DEFAULT '',
        perspective   TEXT    NOT NULL DEFAULT 'system',
        weight        INTEGER,
        concept       TEXT,
        created_by    TEXT    NOT NULL DEFAULT 'define_relationship_ui',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(edge_type, from_table, from_column, to_table, to_column, perspective)
    )
    """,
]

TARGET_TABLES = {"sql_graph_nodes", "sql_graph_edges", "sql_graph_authored_edges"}


def get_existing_tables(conn: sqlite3.Connection) -> set:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def run_migration(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[add_sql_graph_tables] ERROR: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        existing = get_existing_tables(conn)
        already_present = TARGET_TABLES & existing
        to_create = TARGET_TABLES - existing

        if already_present:
            print(f"[add_sql_graph_tables] Already present (skipped): {sorted(already_present)}")
        if not to_create:
            print("[add_sql_graph_tables] Both SQL graph tables already exist — nothing to do.")
            return

        with conn:
            for ddl in DDL_STATEMENTS:
                conn.execute(ddl)

        created = get_existing_tables(conn) & to_create
        print(f"[add_sql_graph_tables] Created: {sorted(created)}")

        missing = to_create - created
        if missing:
            print(f"[add_sql_graph_tables] ERROR: failed to create: {sorted(missing)}", file=sys.stderr)
            sys.exit(1)

        print("[add_sql_graph_tables] Migration complete.")
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
