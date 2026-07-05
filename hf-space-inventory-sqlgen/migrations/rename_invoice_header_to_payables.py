"""Rename invoice_header -> payables.

The table is the accounts-payable header table: it acts like an invoice
header, but the business name for it is "payables". Column names are kept
unchanged (invoice_id, invoice_number, invoice_date, ...), and
payable_line.invoice_id keeps pointing at it — SQLite's ALTER TABLE RENAME
rewrites the FK clause inside payable_line automatically.

Idempotent — safe to re-run:
  * fresh DB built from the updated schema_sqlite.sql already has `payables`
    and no `invoice_header`, so the rename is skipped;
  * an existing DB gets the rename plus bridge/overlay row updates;
  * if an empty `payables` shell exists alongside a populated
    `invoice_header` (app boot applied the new seed DDL before this
    migration ran), the empty shell is dropped first.

Run from hf-space-inventory-sqlgen/:
    python migrations/rename_invoice_header_to_payables.py
"""

import os
import sqlite3
import sys

HF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

OLD = "invoice_header"
NEW = "payables"

NEW_NODE_DESCRIPTION = (
    "Accounts-payable headers (acts as the invoice header) linked to "
    "purchase orders — three-way match and payment status"
)


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def main() -> None:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"[rename-payables] FAIL-CLOSED: DB not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        has_old = table_exists(conn, OLD)
        has_new = table_exists(conn, NEW)

        if has_old and has_new:
            n = conn.execute(f"SELECT COUNT(*) FROM {NEW}").fetchone()[0]
            if n:
                raise SystemExit(
                    f"[rename-payables] FAIL-CLOSED: both {OLD} and {NEW} exist "
                    f"and {NEW} has {n} rows — manual resolution required."
                )
            conn.execute(f"DROP TABLE {NEW}")
            print(f"[rename-payables] dropped empty {NEW} shell")
            has_new = False

        if has_old and not has_new:
            conn.execute(f"ALTER TABLE {OLD} RENAME TO {NEW}")
            print(f"[rename-payables] renamed table {OLD} -> {NEW}")
        elif not has_old and has_new:
            print(f"[rename-payables] table already named {NEW} — skipping rename")
        else:
            raise SystemExit(
                f"[rename-payables] FAIL-CLOSED: neither {OLD} nor {NEW} exists."
            )

        # ── bridge / overlay rows that carry the table name ────────────────
        updates = [
            # (table, set-column, where-column)
            ("schema_nodes",            "table_name", "table_name"),
            ("schema_edges",            "from_table", "from_table"),
            ("schema_edges",            "to_table",   "to_table"),
            ("schema_concept_fields",   "table_name", "table_name"),
            ("api_field_descriptions",  "table_name", "table_name"),
            ("api_table_descriptions",  "table_name", "table_name"),
            ("sql_graph_authored_edges", "from_table", "from_table"),
            ("sql_graph_authored_edges", "to_table",   "to_table"),
        ]
        for tbl, set_col, where_col in updates:
            if not table_exists(conn, tbl):
                continue
            cur = conn.execute(
                f"UPDATE {tbl} SET {set_col}=? WHERE {where_col}=?", (NEW, OLD)
            )
            if cur.rowcount:
                print(f"[rename-payables] {tbl}.{set_col}: {cur.rowcount} row(s) updated")

        # keep the node descriptions aligned with the business name
        if table_exists(conn, "schema_nodes"):
            cur = conn.execute(
                "UPDATE schema_nodes SET description=? WHERE table_name=?",
                (NEW_NODE_DESCRIPTION, NEW),
            )
            if cur.rowcount:
                print("[rename-payables] schema_nodes description refreshed")
            # any other node description that mentions the old table name
            # (e.g. payable_line: "… extending invoice_header …")
            cur = conn.execute(
                "UPDATE schema_nodes SET description = REPLACE(description, ?, ?) "
                "WHERE description LIKE ?",
                (OLD, NEW, f"%{OLD}%"),
            )
            if cur.rowcount:
                print(
                    f"[rename-payables] schema_nodes descriptions mentioning "
                    f"{OLD}: {cur.rowcount} row(s) rewritten"
                )

        conn.commit()
        print("[rename-payables] done")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
