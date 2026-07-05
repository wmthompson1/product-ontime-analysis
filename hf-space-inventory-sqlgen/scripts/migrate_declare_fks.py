"""Declare the structural FOREIGN KEY constraints on the 9 older ERP tables.

Background (v3 canonical, pragma_complete decision)
---------------------------------------------------
The canonical graph metadata (replit_integrations/export_graph_metadata.py)
builds its structural ``references`` edges from PRAGMA-declared foreign keys.
Seven newer tables already carried declared FKs (18 edges); the nine older
tables documented their relationships only in the ``schema_edges`` metadata
table, so PRAGMA never saw them. This migration declares those 19 relationships
as real FK constraints so PRAGMA yields the full 37 — the single authoritative
structural FK source.

SQLite cannot ``ALTER TABLE ... ADD CONSTRAINT``, so each table is recreated:
its exact CREATE statement is reused (preserving every column, default, CHECK
and UNIQUE clause), FK clauses are appended, rows are copied, the old table is
dropped and the new one renamed. Run inside one transaction with foreign-key
enforcement off.

Orphan data is tolerated by design. A declared FK in this DB is a *structural*
schema statement, not a data-validity guarantee: the synthetic dataset has known
``part_id`` dirt (mixed ``P-``/``PN-`` prefixes plus a separate ``PN-100x0``
numbering family that never existed in ``part``, and service codes parked in
``po_line.part_id`` for outside-service lines). This same dirt already lives
under the seven pre-existing declared FKs (e.g. inventory_transaction.part_id),
and runtime foreign-key enforcement is off, so the app is unaffected. This
migration therefore COMMITS the constraints and reports a foreign_key_check
summary rather than rolling back, keeping the canonical ``references`` layer
complete (37 edges).

Idempotent: a table whose CREATE text already contains ``FOREIGN KEY`` is
skipped, so re-running is a no-op.

operation.vendor_id -> suppliers.supplier_id is a cross-named FK (vendor and
supplier are the same entity in this manufacturing model); approved.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(_HERE, "..", "app_schema", "manufacturing.db")

# (child_table, child_col, parent_table, parent_col)
FKS: list[tuple[str, str, str, str]] = [
    ("certification", "part_id", "part", "part_id"),
    ("certification", "receipt_id", "receiving", "receipt_id"),
    ("payables", "po_id", "purchase_order", "po_id"),
    ("payables", "supplier_id", "suppliers", "supplier_id"),
    ("labor_ticket", "wo_id", "work_order", "wo_id"),
    ("material_issue", "part_id", "part", "part_id"),
    ("material_issue", "wo_id", "work_order", "wo_id"),
    ("operation", "resource_id", "shop_resource", "resource_id"),
    ("operation", "service_id", "service", "service_id"),
    ("operation", "vendor_id", "suppliers", "supplier_id"),
    ("operation", "wo_id", "work_order", "wo_id"),
    ("po_line", "part_id", "part", "part_id"),
    ("po_line", "po_id", "purchase_order", "po_id"),
    ("purchase_order", "supplier_id", "suppliers", "supplier_id"),
    ("purchase_order", "wo_id", "work_order", "wo_id"),
    ("receiving", "part_id", "part", "part_id"),
    ("receiving", "po_id", "purchase_order", "po_id"),
    ("receiving", "supplier_id", "suppliers", "supplier_id"),
    ("work_order", "part_id", "part", "part_id"),
]


def _fk_clause(child_col: str, parent_table: str, parent_col: str) -> str:
    return (
        f'FOREIGN KEY ("{child_col}") '
        f'REFERENCES "{parent_table}" ("{parent_col}")'
    )


def _rebuilt_create_sql(original_sql: str, table: str, fk_clauses: list[str]) -> str:
    """Return a CREATE statement for ``table``__mig_new with FK clauses appended.

    The original CREATE text is reused verbatim except for the table name and
    the appended foreign keys, so all columns / defaults / CHECK / UNIQUE
    constraints are preserved exactly.
    """
    tmp = f"{table}__mig_new"
    # Rename only the leading "CREATE TABLE <table>" token (first occurrence).
    needle = f"CREATE TABLE {table}"
    if needle not in original_sql:
        raise ValueError(f"unexpected CREATE text for {table!r}: {original_sql[:60]!r}")
    new_sql = original_sql.replace(needle, f"CREATE TABLE {tmp}", 1)

    close = new_sql.rfind(")")
    if close == -1:
        raise ValueError(f"no closing paren in CREATE for {table!r}")
    body = new_sql[:close].rstrip()
    tail = new_sql[close:]
    fk_block = ",\n    " + ",\n    ".join(fk_clauses)
    return body + fk_block + "\n" + tail


def main(db_path: str) -> int:
    db_path = os.path.abspath(db_path)
    print(f"DB: {db_path}")

    by_table: dict[str, list[tuple[str, str, str]]] = {}
    for child, ccol, ptab, pcol in FKS:
        by_table.setdefault(child, []).append((ccol, ptab, pcol))

    conn = sqlite3.connect(db_path)
    conn.isolation_level = None  # manual transaction control
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = OFF")

    rebuilt: list[str] = []
    skipped: list[str] = []

    conn.execute("BEGIN")
    try:
        for table, fks in by_table.items():
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if row is None:
                raise ValueError(f"table not found: {table}")
            original_sql = row["sql"]

            if "FOREIGN KEY" in original_sql.upper():
                skipped.append(table)
                continue

            before = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            fk_clauses = [_fk_clause(c, p, pc) for (c, p, pc) in fks]
            new_sql = _rebuilt_create_sql(original_sql, table, fk_clauses)

            conn.execute(new_sql)
            conn.execute(
                f'INSERT INTO "{table}__mig_new" SELECT * FROM "{table}"'
            )
            after = conn.execute(
                f'SELECT COUNT(*) FROM "{table}__mig_new"'
            ).fetchone()[0]
            if before != after:
                raise ValueError(
                    f"row count mismatch on {table}: {before} -> {after}"
                )
            conn.execute(f'DROP TABLE "{table}"')
            conn.execute(
                f'ALTER TABLE "{table}__mig_new" RENAME TO "{table}"'
            )
            rebuilt.append(f"{table} (+{len(fk_clauses)} FK, {after} rows)")

        # foreign_key_check rows: (table, rowid, parent, fkid). Pre-existing
        # synthetic-data orphans are tolerated (see module docstring); summarize
        # them per table rather than rolling back.
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        orphan_summary: dict[str, int] = {}
        for v in violations:
            orphan_summary[v[0]] = orphan_summary.get(v[0], 0) + 1

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

    declared = 0
    for t in by_table:
        declared += len(conn.execute(f'PRAGMA foreign_key_list("{t}")').fetchall())
    conn.close()

    print(f"rebuilt: {rebuilt if rebuilt else '(none)'}")
    print(f"skipped (already had FKs): {skipped if skipped else '(none)'}")
    print(f"declared FKs now on the 9 tables: {declared}")
    if orphan_summary:
        print(
            "tolerated pre-existing orphan rows (constraints declared, "
            "not enforced at runtime):"
        )
        for tbl in sorted(orphan_summary):
            print(f"    {tbl}: {orphan_summary[tbl]}")
    else:
        print("no orphan rows — all declared FKs satisfied by data")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB))
