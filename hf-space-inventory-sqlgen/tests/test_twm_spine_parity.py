"""hf-space-inventory-sqlgen/tests/test_twm_spine_parity.py

Spine-parity regression gate for the consolidated Three-Way Match Coverage
view (the "spine"): proves, against the live manufacturing.db, that the
sibling governed exception views remain FILTERS over the spine rather than
drifting into their own populations.

Covers:
  1. The spine executes NULL-bound and its population spans all five match
     states (Not Received / Received-Uninvoiced / Partially Invoiced /
     Matched / Over-Invoiced).
  2. PRA parity: the Partial-Receipt Accrual Exposure view's PO-line
     population equals the spine aggregated per PO line and filtered to the
     accrual condition (received > 0, received < ordered, live voucher
     coverage < received) — quantities included.
  3. Uninvoiced Receipts parity: the UR view's receipt-header population
     equals the receipt headers derived from the spine's under-covered
     receipt-linked rows (qty_invoiced < qty_received) at the UR view's
     SITE-1 scope.
  4. Boundary (asserted, not hidden): voucher lines with NO receipt_line_id
     linkage are EXCLUDED from the spine — they remain the Three-Way Match
     Exceptions view's concern.
  5. Palette wiring: 'Three-Way Match Coverage' is registered in
     schema_intent_queries at the index matching the file's marker order,
     and the mirrored palette SQL returns the same population as the
     governed snippet.

Fails closed on ANY drift.

Run: python -m pytest hf-space-inventory-sqlgen/tests/test_twm_spine_parity.py -q
 or: python hf-space-inventory-sqlgen/tests/test_twm_spine_parity.py
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

SNIPPET_DIR = os.path.join(HF_DIR, "app_schema", "ground_truth", "sql_snippets")
SPINE_PATH = os.path.join(
    SNIPPET_DIR, "payables_threewaymatchcoverage_20260708_000005.sql")
PRA_PATH = os.path.join(
    SNIPPET_DIR, "payables_partialreceiptaccrual_20260708_000004.sql")
UR_PATH = os.path.join(
    SNIPPET_DIR, "payables_uninvoicedreceipts_20260706_000003.sql")
QUERIES_PATH = os.path.join(HF_DIR, "app_schema", "queries",
                            "supplier_performance.sql")
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

NULL_PARAMS = {"supplier_id": None, "start_date": None, "end_date": None}

MATCH_STATES = {"Not Received", "Received-Uninvoiced", "Partially Invoiced",
                "Matched", "Over-Invoiced"}

COVERAGE_NAME = "Three-Way Match Coverage"
INTENT_ID = 18


def _connect() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"manufacturing.db not found at {DB_PATH}. "
            "Run scripts/bootstrap_db.py, then re-run this test.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _spine_rows(conn: sqlite3.Connection) -> list:
    return [dict(r) for r in conn.execute(_read(SPINE_PATH), NULL_PARAMS)]


# ---------------------------------------------------------------------------
# 1. Spine executes and spans the full coverage spectrum
# ---------------------------------------------------------------------------

def test_spine_executes_and_spans_all_five_match_states():
    conn = _connect()
    try:
        rows = _spine_rows(conn)
        assert rows, "spine returned 0 rows NULL-bound"
        states = {r["match_status"] for r in rows}
        assert states == MATCH_STATES, (
            f"spine population must span all five match states, "
            f"got {sorted(states)}")
        # Row grain sanity: every row carries the truth-flag set.
        for r in rows:
            assert r["po_exists"] == 1, "spine is PO-line driven"
            assert r["receipt_exists"] in (0, 1)
            assert r["voucher_exists"] in (0, 1)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. PRA population == spine filtered to the accrual condition
# ---------------------------------------------------------------------------

def _derive_pra_from_spine(rows: list) -> dict:
    """Aggregate spine rows per PO line, keep lines in the PRA condition.

    Returns {po_line_id: (qty_ordered, qty_received, qty_invoiced)} for
    lines with 0 < received < ordered and live voucher coverage < received.
    The spine's qty_invoiced already applies the live-voucher rules
    (cancelled vouchers and post-:end_date vouchers count as no coverage),
    so a plain sum reproduces the PRA view's coverage aggregate.
    """
    agg: dict = {}
    for r in rows:
        a = agg.setdefault(r["po_line_id"],
                           {"ordered": r["qty_ordered"], "rcv": 0.0,
                            "inv": 0.0, "has_receipt": False})
        if r["receipt_exists"]:
            a["has_receipt"] = True
            a["rcv"] += r["qty_received"]
            a["inv"] += r["qty_invoiced"]
    return {
        line: (a["ordered"], round(a["rcv"], 1), round(a["inv"], 1))
        for line, a in agg.items()
        if a["has_receipt"] and 0 < a["rcv"] < a["ordered"]
        and a["inv"] < a["rcv"]
    }


def test_pra_population_equals_spine_filtered_to_accrual_condition():
    conn = _connect()
    try:
        derived = _derive_pra_from_spine(_spine_rows(conn))
        view = {
            r["po_line_id"]: (r["qty_ordered"], r["qty_received"],
                              r["qty_invoiced"])
            for r in conn.execute(_read(PRA_PATH), NULL_PARAMS)
        }
        assert derived, "spine-derived PRA population is empty — the " \
                        "engineered PRA demo lines are missing"
        assert set(view) == set(derived), (
            f"PRA population drift: view PO lines {sorted(view)} vs "
            f"spine-derived {sorted(derived)}")
        for line in view:
            assert view[line] == derived[line], (
                f"PRA quantity drift on PO line {line}: view "
                f"(ordered, received, invoiced)={view[line]} vs "
                f"spine-derived {derived[line]}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. Uninvoiced Receipts population consistent with the spine's
#    under-covered receipt-linked rows
# ---------------------------------------------------------------------------

def test_uninvoiced_receipts_population_consistent_with_spine():
    conn = _connect()
    try:
        rows = _spine_rows(conn)
        # The UR view is scoped to SITE-1 and reports receipt HEADERS with
        # >= 1 line whose live voucher coverage is short of the received
        # quantity. Derive the same population from the spine: receipt-linked
        # rows with qty_invoiced < qty_received, mapped line -> header.
        line_to_receipt = {
            r["receipt_line_id"]: r["receipt_id"]
            for r in conn.execute(
                "SELECT receipt_line_id, receipt_id FROM receiving_line")
        }
        derived = set()
        for r in rows:
            if not r["receipt_exists"]:
                continue
            if r["site_id"] != "SITE-1":
                continue
            if r["qty_invoiced"] < r["qty_received"]:
                receipt_id = line_to_receipt.get(r["receipt_line_id"])
                assert receipt_id is not None, (
                    f"spine receipt line {r['receipt_line_id']} has no "
                    f"receiving_line header linkage")
                derived.add(receipt_id)
        view = {r["receiver_id"]
                for r in conn.execute(_read(UR_PATH), NULL_PARAMS)}
        assert view, "Uninvoiced Receipts view is empty — the engineered " \
                     "uninvoiced demo populations are missing"
        assert view == derived, (
            f"Uninvoiced Receipts population drift: view receipts "
            f"{sorted(view)} vs spine-derived {sorted(derived)}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Boundary: voucher lines without a receipt-line linkage are EXCLUDED
#    from the spine (they remain the Exceptions view's concern)
# ---------------------------------------------------------------------------

def test_orphan_voucher_lines_excluded_from_spine():
    conn = _connect()
    try:
        orphans = [r["payable_line_id"] for r in conn.execute(
            "SELECT payable_line_id FROM payable_line "
            "WHERE receipt_line_id IS NULL")]
        assert orphans, (
            "expected at least one voucher line without receipt_line_id "
            "(the engineered TWM-exception boundary case) — the boundary "
            "this gate asserts no longer exists in the data")
        rows = _spine_rows(conn)
        # The spine's voucher leg joins strictly on
        # payable_line.receipt_line_id = receiving_line.receipt_line_id, so
        # every vouchered spine row must map back to a payable_line WITH a
        # receipt linkage; orphan voucher invoices must not surface.
        orphan_invoices = {r["invoice_number"] for r in conn.execute(
            """SELECT pay.invoice_number AS invoice_number
               FROM payable_line pl
               JOIN payables pay ON pay.invoice_id = pl.invoice_id
               WHERE pl.receipt_line_id IS NULL""")}
        linked_invoices = {r["invoice_number"] for r in conn.execute(
            """SELECT pay.invoice_number AS invoice_number
               FROM payable_line pl
               JOIN payables pay ON pay.invoice_id = pl.invoice_id
               WHERE pl.receipt_line_id IS NOT NULL""")}
        spine_invoices = {r["invoice_number"] for r in rows
                          if r["voucher_exists"]}
        leaked = spine_invoices & (orphan_invoices - linked_invoices)
        assert not leaked, (
            f"orphan voucher lines leaked into the spine via invoices "
            f"{sorted(leaked)} — voucher lines without receipt_line_id are "
            f"the Exceptions view's concern, not the spine's")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Palette wiring: registered, index-consistent, SQL mirrors the snippet
# ---------------------------------------------------------------------------

def _extract_palette_query(sql_text: str, name: str) -> str:
    marker = f"-- Query: {name}"
    start = sql_text.index(marker)
    body_start = sql_text.index("\n", start) + 1
    m = re.search(r"^(?!--)", sql_text[body_start:], re.M)
    body_start += m.start()
    end = sql_text.index(";", body_start)
    return sql_text[body_start:end + 1]


def test_coverage_palette_wiring_matches_file_order():
    conn = _connect()
    try:
        palette_text = _read(QUERIES_PATH)
        names = [line.replace("-- Query:", "").strip()
                 for line in palette_text.splitlines()
                 if line.startswith("-- Query:")]
        assert COVERAGE_NAME in names, (
            f"'-- Query: {COVERAGE_NAME}' marker missing from "
            f"supplier_performance.sql")
        file_index = names.index(COVERAGE_NAME)
        row = conn.execute(
            """SELECT query_index FROM schema_intent_queries
               WHERE intent_id = ? AND query_file = 'supplier_performance.sql'
                 AND query_name = ?""",
            (INTENT_ID, COVERAGE_NAME)).fetchone()
        assert row is not None, (
            f"'{COVERAGE_NAME}' is not wired in schema_intent_queries — "
            f"run migrations/add_twm_coverage_palette.py")
        assert row["query_index"] == file_index, (
            f"palette wiring index {row['query_index']} != file marker "
            f"index {file_index}")
        # No two wired entries for this file may share an index.
        dupes = conn.execute(
            """SELECT query_index, COUNT(*) AS n FROM schema_intent_queries
               WHERE query_file = 'supplier_performance.sql'
               GROUP BY query_index HAVING n > 1""").fetchall()
        assert not dupes, (
            f"duplicate query_index values wired for "
            f"supplier_performance.sql: {[dict(d) for d in dupes]}")
    finally:
        conn.close()


def test_coverage_palette_sql_mirrors_governed_snippet():
    conn = _connect()
    try:
        palette_sql = _extract_palette_query(_read(QUERIES_PATH),
                                             COVERAGE_NAME)
        palette_rows = conn.execute(palette_sql, NULL_PARAMS).fetchall()
        snippet_rows = conn.execute(_read(SPINE_PATH), NULL_PARAMS).fetchall()
        assert palette_rows, "palette Coverage query returned 0 rows"
        assert [tuple(r) for r in palette_rows] == \
               [tuple(r) for r in snippet_rows], (
            f"palette Coverage query drifted from the governed snippet "
            f"({len(palette_rows)} vs {len(snippet_rows)} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All twm_spine_parity tests passed.")
