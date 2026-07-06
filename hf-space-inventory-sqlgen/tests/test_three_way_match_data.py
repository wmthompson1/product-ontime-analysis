"""Tests for the completed three-way match chain against the REAL
manufacturing.db (migrations/complete_three_way_match.py output).

These lock in the data contract:

  * every Closed PO with lines is fully received at line level,
  * receiving headers and lines never drift (part / quantities agree),
  * every invoice's amount equals the sum of its payable lines,
  * every payable line of a Matched invoice links to a receipt line whose
    received quantity covers the billed quantity,
  * an unpaid Exception invoice exists with a genuine short-receipt
    mismatch (received < billed on a linked line),
  * all five demo populations are non-empty: unreceived POs, clean matches,
    invoiced-voucher-pending, received-not-invoiced, unpaid exceptions,
  * MRP-critical POs carry no receipts,
  * the three-way-match ground-truth queries in supplier_performance.sql
    (Supplier AP Total Due / AP Aging by Supplier / Three-Way Match
    Exceptions) each return at least one row,
  * the migration is idempotent (a re-run changes nothing).

Run: python hf-space-inventory-sqlgen/tests/test_three_way_match_data.py
Skips (exit 0 with a notice) if manufacturing.db is missing — fresh clones
build it with scripts/bootstrap_db.py.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
QUERIES_SQL = os.path.join(HF_DIR, "app_schema", "queries",
                           "supplier_performance.sql")

PROTECTED_POS = ("PO-MRP-BLK1", "PO-MRP-BLK2", "PO-MRP-BLK3",
                 "PO-MRP-P-10032", "PO-CON-001")

THREE_WAY_QUERY_NAMES = (
    "Supplier AP Total Due",
    "AP Aging by Supplier",
    "Three-Way Match Exceptions",
)


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_closed_pos_fully_received():
    conn = _connect()
    try:
        n = _one(conn, """
            SELECT COUNT(*) FROM po_line pl
            JOIN purchase_order po ON po.po_id = pl.po_id
            WHERE po.status='Closed'
              AND NOT EXISTS (SELECT 1 FROM receiving_line rl
                              WHERE rl.po_line_id = pl.line_id
                                AND rl.quantity_received >= pl.quantity)
        """)
        assert n == 0, f"{n} Closed PO line(s) not fully received"
    finally:
        conn.close()


def test_receiving_header_line_consistency():
    conn = _connect()
    try:
        drift = _one(conn, """
            SELECT COUNT(*) FROM receiving r
            JOIN receiving_line rl USING(receipt_id)
            WHERE r.part_id <> rl.part_id
               OR r.quantity_received <> rl.quantity_received
               OR r.quantity_ordered <> rl.quantity_ordered
        """)
        assert drift == 0, f"{drift} header/line drift row(s)"
        headless = _one(conn, """
            SELECT COUNT(*) FROM receiving r
            WHERE NOT EXISTS (SELECT 1 FROM receiving_line rl
                              WHERE rl.receipt_id = r.receipt_id)
        """)
        assert headless == 0, f"{headless} receipt header(s) without lines"
    finally:
        conn.close()


def test_invoice_amounts_reconcile():
    conn = _connect()
    try:
        n = _one(conn, """
            SELECT COUNT(*) FROM payables p
            WHERE ABS(p.amount_dollars - (SELECT COALESCE(SUM(l.amount),0)
                                          FROM payable_line l
                                          WHERE l.invoice_id = p.invoice_id)) > 0.01
        """)
        assert n == 0, f"{n} invoice(s) drift from their line sums"
    finally:
        conn.close()


def test_matched_invoices_fully_linked_and_covered():
    conn = _connect()
    try:
        n = _one(conn, """
            SELECT COUNT(*) FROM payable_line l
            JOIN payables p ON p.invoice_id = l.invoice_id
            WHERE p.three_way_match_status = 'Matched'
              AND (l.receipt_line_id IS NULL
                   OR (SELECT rl.quantity_received FROM receiving_line rl
                       WHERE rl.receipt_line_id = l.receipt_line_id) < l.qty)
        """)
        assert n == 0, f"{n} Matched payable line(s) unlinked or short"
    finally:
        conn.close()


def test_exception_has_genuine_mismatch():
    conn = _connect()
    try:
        n = _one(conn, """
            SELECT COUNT(*) FROM payables p
            WHERE p.three_way_match_status = 'Exception'
              AND p.status IN ('Open','Disputed')
              AND EXISTS (
                  SELECT 1 FROM payable_line l
                  JOIN receiving_line rl ON rl.receipt_line_id = l.receipt_line_id
                  WHERE l.invoice_id = p.invoice_id
                    AND rl.quantity_received < l.qty)
        """)
        assert n >= 1, "no unpaid Exception invoice with a real short-receipt"
        bogus = _one(conn, """
            SELECT COUNT(*) FROM payables p
            WHERE p.three_way_match_status = 'Exception'
              AND EXISTS (SELECT 1 FROM payable_line l
                          WHERE l.invoice_id = p.invoice_id)
              AND NOT EXISTS (
                  SELECT 1 FROM payable_line l
                  JOIN receiving_line rl ON rl.receipt_line_id = l.receipt_line_id
                  WHERE l.invoice_id = p.invoice_id
                    AND rl.quantity_received < l.qty)
        """)
        assert bogus == 0, f"{bogus} Exception invoice(s) without a mismatch"
    finally:
        conn.close()


def test_all_populations_present():
    conn = _connect()
    try:
        pops = {
            "unreceived POs": """
                SELECT COUNT(*) FROM purchase_order po
                WHERE po.status='Open'
                  AND NOT EXISTS (SELECT 1 FROM receiving r WHERE r.po_id=po.po_id)
                  AND NOT EXISTS (SELECT 1 FROM payables p WHERE p.po_id=po.po_id)
            """,
            "clean paid matches": """
                SELECT COUNT(*) FROM payables
                WHERE three_way_match_status='Matched' AND status='Paid'
            """,
            "invoiced voucher pending": """
                SELECT COUNT(*) FROM payables
                WHERE three_way_match_status='Pending' AND payment_date IS NULL
            """,
            "received not invoiced": """
                SELECT COUNT(DISTINCT r.po_id) FROM receiving r
                WHERE NOT EXISTS (SELECT 1 FROM payables p WHERE p.po_id=r.po_id)
            """,
            "unpaid exceptions": """
                SELECT COUNT(*) FROM payables
                WHERE three_way_match_status='Exception'
                  AND status IN ('Open','Disputed')
            """,
        }
        for name, sql in pops.items():
            n = _one(conn, sql)
            assert n >= 1, f"population empty: {name}"
        paid_pending = _one(conn, """
            SELECT COUNT(*) FROM payables
            WHERE status='Paid' AND three_way_match_status='Pending'
        """)
        assert paid_pending == 0, f"{paid_pending} Paid invoice(s) still Pending"
    finally:
        conn.close()


def test_no_dangling_links():
    conn = _connect()
    try:
        for label, sql in {
            "payable_line->receiving_line": """
                SELECT COUNT(*) FROM payable_line l
                WHERE l.receipt_line_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM receiving_line rl
                                  WHERE rl.receipt_line_id = l.receipt_line_id)
            """,
            "receiving_line->po_line": """
                SELECT COUNT(*) FROM receiving_line rl
                WHERE rl.po_line_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM po_line pl
                                  WHERE pl.line_id = rl.po_line_id)
            """,
            "receiving->purchase_order": """
                SELECT COUNT(*) FROM receiving r
                WHERE NOT EXISTS (SELECT 1 FROM purchase_order po
                                  WHERE po.po_id = r.po_id)
            """,
        }.items():
            n = _one(conn, sql)
            assert n == 0, f"{n} dangling {label} link(s)"
    finally:
        conn.close()


def test_protected_pos_untouched():
    conn = _connect()
    try:
        marks = ",".join("?" * len(PROTECTED_POS))
        n = _one(conn,
                 f"SELECT COUNT(*) FROM receiving WHERE po_id IN ({marks})",
                 PROTECTED_POS)
        assert n == 0, f"{n} receipt(s) on MRP-protected POs"
    finally:
        conn.close()


def _extract_query(sql_text: str, name: str) -> str:
    marker = f"-- Query: {name}"
    start = sql_text.index(marker)
    body_start = sql_text.index("\n", start) + 1
    # skip the description comment lines
    m = re.search(r"^(?!--)", sql_text[body_start:], re.M)
    body_start += m.start()
    end = sql_text.index(";", body_start)
    return sql_text[body_start:end + 1]


def test_three_way_ground_truth_queries_return_rows():
    with open(QUERIES_SQL) as f:
        sql_text = f.read()
    conn = _connect()
    try:
        for name in THREE_WAY_QUERY_NAMES:
            q = _extract_query(sql_text, name)
            rows = conn.execute(q, {"supplier_id": None}).fetchall()
            assert rows, f"ground-truth query returned no rows: {name}"
    finally:
        conn.close()


def test_migration_idempotent():
    import subprocess
    conn = _connect()
    try:
        before = (
            _one(conn, "SELECT COUNT(*) FROM receiving"),
            _one(conn, "SELECT COUNT(*) FROM receiving_line"),
            _one(conn, "SELECT COUNT(*) FROM payable_line"),
            _one(conn, "SELECT COALESCE(SUM(amount_dollars),0) FROM payables"),
        )
    finally:
        conn.close()
    r = subprocess.run(
        [sys.executable, os.path.join(HF_DIR, "migrations",
                                      "complete_three_way_match.py")],
        cwd=HF_DIR, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"re-run failed:\n{r.stdout}\n{r.stderr}"
    conn = _connect()
    try:
        after = (
            _one(conn, "SELECT COUNT(*) FROM receiving"),
            _one(conn, "SELECT COUNT(*) FROM receiving_line"),
            _one(conn, "SELECT COUNT(*) FROM payable_line"),
            _one(conn, "SELECT COALESCE(SUM(amount_dollars),0) FROM payables"),
        )
    finally:
        conn.close()
    assert before == after, f"re-run changed data: {before} -> {after}"


def main() -> int:
    if not os.path.exists(DB_PATH):
        print("SKIP  manufacturing.db missing — run scripts/bootstrap_db.py first")
        return 0
    conn = _connect()
    try:
        has_lines = _one(conn, """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='receiving_line'
        """)
    finally:
        conn.close()
    if not has_lines:
        print("SKIP  receiving_line missing — run "
              "migrations/add_receiving_line_and_commodities.py first")
        return 0

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {t.__name__}: {exc}")
    total = len(tests)
    print(f"\n{total - failures}/{total} three-way match tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
