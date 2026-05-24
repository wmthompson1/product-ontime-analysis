"""
install_sync_triggers.py
========================
Installs SQLite triggers on the three bridge tables that feed ArangoDB:
  - schema_intent_perspectives
  - schema_perspective_concepts
  - schema_intent_concepts

Each trigger writes a row to `graph_sync_queue` whenever rows are
inserted, updated, or deleted.  `sync_watcher.py` polls that queue
and calls graph_sync.sync_graph() automatically.

Usage:
    python hf-space-inventory-sqlgen/scripts/install_sync_triggers.py
    python hf-space-inventory-sqlgen/scripts/install_sync_triggers.py --verify
    python hf-space-inventory-sqlgen/scripts/install_sync_triggers.py --remove
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app_schema", "manufacturing.db"
)

CREATE_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS graph_sync_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    queued_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_table TEXT NOT NULL,
    operation   TEXT NOT NULL,   -- INSERT / UPDATE / DELETE
    processed   INTEGER DEFAULT 0,
    processed_at DATETIME,
    sync_outcome TEXT            -- SUCCESS / FAILED / <error message>
);
"""

WATCHED_TABLES = [
    "schema_intent_perspectives",
    "schema_perspective_concepts",
    "schema_intent_concepts",
]

OPERATIONS = ["INSERT", "UPDATE", "DELETE"]


def trigger_name(table: str, op: str) -> str:
    return f"trg_arango_sync_{table}_{op.lower()}"


def make_trigger_sql(table: str, op: str) -> str:
    timing = "AFTER"
    name = trigger_name(table, op)
    return (
        f"CREATE TRIGGER IF NOT EXISTS {name}\n"
        f"  {timing} {op} ON {table}\n"
        f"  BEGIN\n"
        f"    INSERT INTO graph_sync_queue (source_table, operation)\n"
        f"    VALUES ('{table}', '{op}');\n"
        f"  END;"
    )


def drop_trigger_sql(table: str, op: str) -> str:
    return f"DROP TRIGGER IF EXISTS {trigger_name(table, op)};"


def install(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_QUEUE_TABLE)
    for table in WATCHED_TABLES:
        for op in OPERATIONS:
            sql = make_trigger_sql(table, op)
            conn.execute(sql)
            print(f"  [OK] trigger installed: {trigger_name(table, op)}")
    conn.commit()


def remove(conn: sqlite3.Connection) -> None:
    for table in WATCHED_TABLES:
        for op in OPERATIONS:
            conn.execute(drop_trigger_sql(table, op))
            print(f"  [REMOVED] {trigger_name(table, op)}")
    conn.commit()


def verify(conn: sqlite3.Connection) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_arango_sync_%'"
    ).fetchall()
    found = {r[0] for r in rows}
    expected = {trigger_name(t, op) for t in WATCHED_TABLES for op in OPERATIONS}
    missing = expected - found

    queue_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_sync_queue'"
    ).fetchone()

    print(f"  graph_sync_queue table: {'EXISTS' if queue_exists else 'MISSING'}")
    print(f"  Expected triggers : {len(expected)}")
    print(f"  Installed triggers: {len(found)}")

    if missing:
        print("  MISSING triggers:")
        for t in sorted(missing):
            print(f"    - {t}")
        return False

    print("  All triggers are installed correctly.")
    return True


def main() -> None:
    mode = "--verify" if "--verify" in sys.argv else (
        "--remove" if "--remove" in sys.argv else "--install"
    )

    if not os.path.exists(DB_PATH):
        print(f"ERROR: database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        if mode == "--install":
            print(f"Installing sync triggers into {DB_PATH} ...")
            install(conn)
            print("Done. Verifying ...")
            ok = verify(conn)
            sys.exit(0 if ok else 1)

        elif mode == "--verify":
            print(f"Verifying sync triggers in {DB_PATH} ...")
            ok = verify(conn)
            sys.exit(0 if ok else 1)

        elif mode == "--remove":
            print(f"Removing sync triggers from {DB_PATH} ...")
            remove(conn)
            print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
