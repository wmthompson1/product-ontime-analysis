"""Tests for the two governed procurement receiving views:

  * payables_ordersreceived_20260706_000001   — POs fully received
  * payables_ordersunreceived_20260706_000002 — POs unreceived or short

Contract locked in:
  * both snippets are APPROVED manifest entries whose SQL executes,
  * against the live DB the two result sets are disjoint over po_id and
    exclude Cancelled POs,
  * every "received" row shows qty_received >= qty_ordered,
  * every "unreceived" row shows qty_outstanding > 0,
  * clamp regression (synthetic in-memory DB): an over-received line never
    offsets another line's shortage — qty_outstanding sums per-line
    MAX(ordered - received, 0), so mixed over/short POs report the true
    open quantity, never a netted or negative one.

Run: python hf-space-inventory-sqlgen/tests/test_procurement_views.py
Skips (exit 0) if manufacturing.db or the manifest entries are missing.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
MANIFEST_PATH = os.path.join(
    HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")

RECEIVED_KEY = "payables_ordersreceived_20260706_000001"
UNRECEIVED_KEY = "payables_ordersunreceived_20260706_000002"


def _load_sql(binding_key: str) -> str:
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)
    entry = manifest["approved_snippets"][binding_key]
    assert entry["validation_status"] == "APPROVED", f"{binding_key} not APPROVED"
    with open(os.path.join(HF_DIR, entry["file_path"]), encoding="utf-8") as fh:
        return fh.read()


def _rows(conn, sql):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def test_result_sets_disjoint_and_no_cancelled():
    conn = sqlite3.connect(DB_PATH)
    try:
        received = _rows(conn, _load_sql(RECEIVED_KEY))
        unreceived = _rows(conn, _load_sql(UNRECEIVED_KEY))
        got = {r["po_id"] for r in received}
        open_ = {r["po_id"] for r in unreceived}
        overlap = got & open_
        assert not overlap, f"POs in both views: {overlap}"
        assert all(r["status"] != "Cancelled" for r in received + unreceived), (
            "Cancelled PO leaked into a view")
        assert received and unreceived, "a view returned no rows on the demo DB"
    finally:
        conn.close()


def test_received_rows_fully_covered():
    conn = sqlite3.connect(DB_PATH)
    try:
        for r in _rows(conn, _load_sql(RECEIVED_KEY)):
            assert r["qty_received"] >= r["qty_ordered"], (
                f"{r['po_id']}: received {r['qty_received']} < ordered {r['qty_ordered']}")
    finally:
        conn.close()


def test_unreceived_rows_have_positive_outstanding():
    conn = sqlite3.connect(DB_PATH)
    try:
        for r in _rows(conn, _load_sql(UNRECEIVED_KEY)):
            assert r["qty_outstanding"] > 0, (
                f"{r['po_id']}: qty_outstanding {r['qty_outstanding']} not > 0")
            assert r["lines_unreceived"] + r["lines_short"] > 0, (
                f"{r['po_id']}: no short/unreceived lines yet in the view")
    finally:
        conn.close()


def test_overreceipt_never_offsets_shortage():
    """Synthetic clamp regression: PO with one line over-received (+5) and one
    line short (-10) must report qty_outstanding = 10, not 5 or -5."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript("""
            CREATE TABLE purchase_order (po_id TEXT PRIMARY KEY, supplier_id TEXT,
                status TEXT, required_date DATE);
            CREATE TABLE po_line (line_id INTEGER PRIMARY KEY, po_id TEXT,
                quantity REAL);
            CREATE TABLE receiving (receipt_id INTEGER PRIMARY KEY,
                receipt_date DATE);
            CREATE TABLE receiving_line (receipt_line_id INTEGER PRIMARY KEY,
                receipt_id INTEGER, po_line_id INTEGER, quantity_received REAL);
            INSERT INTO purchase_order VALUES ('PO-X', 'S-1', 'Partial', '2026-01-01');
            INSERT INTO po_line VALUES (1, 'PO-X', 20), (2, 'PO-X', 30);
            INSERT INTO receiving VALUES (1, '2026-01-02');
            -- line 1 over-received by 5; line 2 short by 10
            INSERT INTO receiving_line VALUES (1, 1, 1, 25), (2, 1, 2, 20);
        """)
        rows = _rows(conn, _load_sql(UNRECEIVED_KEY))
        assert len(rows) == 1 and rows[0]["po_id"] == "PO-X", f"unexpected rows: {rows}"
        assert rows[0]["qty_outstanding"] == 10.0, (
            f"clamp broken: qty_outstanding {rows[0]['qty_outstanding']} != 10.0")
        assert rows[0]["lines_short"] == 1 and rows[0]["lines_unreceived"] == 0
        got = _rows(conn, _load_sql(RECEIVED_KEY))
        assert not got, f"mixed short/over PO wrongly counted as received: {got}"
    finally:
        conn.close()


def main() -> int:
    if not os.path.exists(DB_PATH):
        print("SKIP  manufacturing.db missing — run scripts/bootstrap_db.py first")
        return 0
    try:
        _load_sql(RECEIVED_KEY)
        _load_sql(UNRECEIVED_KEY)
    except KeyError:
        print("SKIP  procurement view manifest entries not present")
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
    print(f"\n{total - failures}/{total} procurement view tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
