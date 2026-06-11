"""Generate a faithful SQL dump (DDL + INSERTs) of the canonical graph source tables.

The three SQLite tables ``sql_graph_nodes`` / ``sql_graph_edges`` /
``sql_graph_authored_edges`` are the source of truth for the canonical graph.
This script serializes them to ``replit_integrations/sql_graph_tables.sql`` — a
flat SQL representation alongside ``graph_metadata.json`` and ``graph_triples.tsv``.

Rows are ordered by the exporter's emission order (``ordinal``) so the output is
diff-stable and parity-friendly. Re-running the produced .sql against a fresh
SQLite database reconstructs the tables byte-for-byte.

Run:
    python replit_integrations/generate_sql_graph_dump.py
"""
from __future__ import annotations

import datetime
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO, "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db")
OUT_PATH = os.path.join(HERE, "sql_graph_tables.sql")
TABLES = ["sql_graph_nodes", "sql_graph_edges", "sql_graph_authored_edges"]


def _lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, bytes):
        return "X'" + v.hex() + "'"
    return "'" + str(v).replace("'", "''") + "'"


def _qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_ddl(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    if row is None or not row["sql"]:
        raise SystemExit(f"table not found: {name}")
    sql = row["sql"].strip()
    if sql.upper().startswith("CREATE TABLE ") and "IF NOT EXISTS" not in sql.upper():
        sql = "CREATE TABLE IF NOT EXISTS " + sql[len("CREATE TABLE "):]
    return sql + ";"


def _order_clause(cols) -> str:
    if "ordinal" in cols:
        return " ORDER BY ordinal, _key"
    if "authored_id" in cols:
        return " ORDER BY authored_id"
    return ""


def generate(db_path: str = DB_PATH, out_path: str = OUT_PATH) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        counts: dict[str, int] = {}
        parts: list[str] = []
        for t in TABLES:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
            rows = conn.execute(f'SELECT * FROM "{t}"' + _order_clause(cols)).fetchall()
            counts[t] = len(rows)
            col_list = ", ".join(_qi(c) for c in cols)
            block = [
                "-- " + "-" * 70,
                f"-- Table: {t}  ({len(rows)} rows)",
                "-- " + "-" * 70,
                "DROP TABLE IF EXISTS " + _qi(t) + ";",
                _table_ddl(conn, t),
                "",
            ]
            if rows:
                for r in rows:
                    vals = ", ".join(_lit(r[c]) for c in cols)
                    block.append(f"INSERT INTO {_qi(t)} ({col_list}) VALUES ({vals});")
            else:
                block.append(f"-- (no rows in {t})")
            block.append("")
            parts.append("\n".join(block))

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        header = [
            "-- ============================================================================",
            "-- Canonical graph source tables — DDL + data",
            "-- ============================================================================",
            "-- GENERATED FILE — do not hand-edit. Regenerate with:",
            "--     python replit_integrations/generate_sql_graph_dump.py",
            "--",
            "-- A faithful SQL dump of the three SQLite tables that are the source of",
            "-- truth for the canonical graph — another flat representation of the same",
            "-- graph alongside graph_metadata.json and graph_triples.tsv.",
            "--",
            f"-- Generated : {ts} (UTC)",
            f"-- Rows      : sql_graph_nodes={counts['sql_graph_nodes']}, "
            f"sql_graph_edges={counts['sql_graph_edges']}, "
            f"sql_graph_authored_edges={counts['sql_graph_authored_edges']}",
            "--",
            "-- Row order matches the exporter's emission order (ORDER BY ordinal) so",
            "-- this file is diff-stable and parity-friendly.",
            "-- ============================================================================",
            "",
            "PRAGMA foreign_keys = OFF;",
            "BEGIN TRANSACTION;",
            "",
        ]
        footer = ["COMMIT;", ""]
        with open(out_path, "w") as f:
            f.write("\n".join(header))
            f.write("\n".join(parts))
            f.write("\n".join(footer))
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    counts = generate()
    print(f"Wrote {OUT_PATH}")
    for t in TABLES:
        print(f"  {t:28s} {counts[t]:5d} rows")
