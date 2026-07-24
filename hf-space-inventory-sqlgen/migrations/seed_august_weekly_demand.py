"""Synthetic weekly August 2026 demand for the three highest on-hand-value parts.

Why: the three parts holding the most on-hand inventory VALUE (signed ledger
net x unit_cost) had thin forward demand, so the MRP grid never showed that
stock being consumed. A deterministic weekly demand series (Aug 7 / 14 / 21,
2026) draws each part's on-hand down and forces planned orders — a visible
netting story in the very first horizon bucket after the AS_OF anchor
(2026-07-31, from the July throughput series).

Selection (computed once from the planning on-hand the MRP grid actually
uses — part.on_hand_qty x unit_cost — then baked as literals; the rebuild
path must not depend on transient state):
    P-10037  Composite Fuselage Skin Section   on-hand 61.6 x $9,200 = $566,720
    P-10014  Inconel 718 Turbine Blade Blank   on-hand 62.4 x $6,800 = $424,320
    P-10024  Machined Housing — Fuel Control   on-hand 48.0 x $8,500 = $408,000

What it does (deterministic — no randomness; idempotent — safe to re-run):

1. DEMAND LINES — nine customer-order lines (3 parts x 3 weekly need-by
   dates) attach to CO-MRP-002, the purpose-built Open MRP demand order.
   Growth is via LINES on an existing header — customer-order headers stay
   in the demo band [10, 20] and AS_OF never moves. Weekly quantities are
   sized so each part's August total exceeds its on-hand, guaranteeing a
   planned-order shortfall after netting:
       P-10037  24 + 24 + 24 = 72  (> 61.6 on hand)
       P-10014  24 + 24 + 24 = 72  (> 62.4 on hand)
       P-10024  18 + 18 + 18 = 54  (> 48.0 on hand)
   desired_release = need_by - part.lead_time_days (90/90/21 days, so the
   releases land before the anchor — honest past-due releases, exactly what
   lot-for-lot lead-time offsetting produces for long-lead parts; lead
   times are 90 / 90 / 60 days).

2. FAIL-CLOSED VERIFY — AS_OF unchanged, customer-order header band [10, 20]
   intact, each of the nine lines present exactly once, every targeted part's
   recomputed MRP grid shows Planned Order Receipts > 0 and a projected
   balance drawn below starting on-hand but never below safety stock, and
   mrp_engine.validate_planning_inputs still passes. Nothing commits unless
   every check holds.
"""

import os
import sqlite3
import sys
from datetime import date, timedelta

HF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

sys.path.insert(0, HF_DIR)

PRICE_MARKUP = 1.35  # sell price = unit_cost * markup (matches expand migration)

ORDER_ID = "CO-MRP-002"  # Pacific Turbine Systems — Open MRP demand order

# (part_id, order_qty, need_by ISO) — weekly August 2026 series, baked literals.
DEMAND_LINES = [
    ("P-10037", 24.0, "2026-08-07"),
    ("P-10037", 24.0, "2026-08-14"),
    ("P-10037", 24.0, "2026-08-21"),
    ("P-10014", 24.0, "2026-08-07"),
    ("P-10014", 24.0, "2026-08-14"),
    ("P-10014", 24.0, "2026-08-21"),
    ("P-10024", 18.0, "2026-08-07"),
    ("P-10024", 18.0, "2026-08-14"),
    ("P-10024", 18.0, "2026-08-21"),
]

PART_IDS = ("P-10037", "P-10014", "P-10024")


def _next_line_no(cur, order_id):
    row = cur.execute(
        "SELECT COALESCE(MAX(line_no), 0) FROM customer_order_line WHERE order_id=?",
        (order_id,),
    ).fetchone()
    return (row[0] or 0) + 1


def add_demand(cur):
    order = cur.execute(
        "SELECT status, site_id FROM customer_order WHERE order_id=?",
        (ORDER_ID,),
    ).fetchone()
    if not order:
        raise SystemExit(f"FAIL-CLOSED: customer order {ORDER_ID} not found")
    if order[0] != "Open":
        raise SystemExit(
            f"FAIL-CLOSED: {ORDER_ID} is '{order[0]}', demand must attach to an Open order"
        )
    site_id = order[1]

    added = 0
    for part_id, qty, need_by in DEMAND_LINES:
        prow = cur.execute(
            "SELECT unit_cost, lead_time_days FROM part WHERE part_id=?", (part_id,)
        ).fetchone()
        if not prow:
            raise SystemExit(f"FAIL-CLOSED: part {part_id} not found")
        unit_cost, lead = prow

        # Idempotent: skip if this exact demand line already exists.
        if cur.execute(
            "SELECT 1 FROM customer_order_line "
            "WHERE order_id=? AND part_id=? AND need_by_date=? AND order_qty=?",
            (ORDER_ID, part_id, need_by, qty),
        ).fetchone():
            continue

        release = date.fromisoformat(need_by) - timedelta(days=int(lead or 0))
        cur.execute(
            "INSERT INTO customer_order_line "
            "(order_id, line_no, part_id, site_id, order_qty, unit_price, "
            " need_by_date, desired_release_date) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ORDER_ID, _next_line_no(cur, ORDER_ID), part_id, site_id, qty,
             round((unit_cost or 0) * PRICE_MARKUP, 2), need_by, release.isoformat()),
        )
        added += 1
    return added


def verify(conn, as_of_before):
    import mrp_engine as mrp

    cur = conn.cursor()
    errors = []

    if mrp.compute_as_of(conn) != as_of_before:
        errors.append(f"AS_OF moved from {as_of_before}")

    co_n = cur.execute(
        "SELECT COUNT(*) FROM customer_order WHERE order_id NOT LIKE 'CO-JUL-%'"
    ).fetchone()[0]
    if not (10 <= co_n <= 20):
        errors.append(f"customer-order headers out of band: {co_n}")

    for part_id, qty, need_by in DEMAND_LINES:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM customer_order_line "
            "WHERE order_id=? AND part_id=? AND need_by_date=? AND order_qty=?",
            (ORDER_ID, part_id, need_by, qty),
        ).fetchone()[0]
        if cnt != 1:
            errors.append(
                f"{part_id}: expected exactly 1 demand line for {need_by}, found {cnt}"
            )

    for part_id in PART_IDS:
        grid = mrp.compute_mrp_grid(conn, part_id)
        rows = dict(grid["rows"])
        on_hand = grid["on_hand_qty"] or 0
        receipts = sum(rows["Planned Order Receipts"])
        pab = rows["Projected Available Balance"]
        safety = grid["safety_stock"]
        if receipts <= 0:
            errors.append(
                f"{part_id}: no planned order receipts (demand did not exceed supply)"
            )
        if not (min(pab) < on_hand):
            errors.append(
                f"{part_id}: on-hand not drawn down (min PAB {min(pab)} >= on_hand {on_hand})"
            )
        if min(pab) < safety - 1e-6:
            errors.append(
                f"{part_id}: projected balance {min(pab)} fell below safety stock {safety}"
            )

    try:
        summary = mrp.validate_planning_inputs(conn)
        print(f"  verify: MRP planning gate OK — {summary['demand_parts']} planning parts")
    except ValueError as exc:
        errors.append(f"MRP planning gate failed: {exc}")

    if errors:
        for e in errors:
            print(f"  VERIFY FAIL: {e}")
        raise SystemExit("FAIL-CLOSED: August weekly-demand verification failed")
    print("  verify: weekly August demand nets on-hand and forces planned orders")


def run():
    import mrp_engine as mrp

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        as_of_before = mrp.compute_as_of(conn)
        print(f"  AS_OF = {as_of_before}")

        added = add_demand(cur)
        print(f"  demand lines added: {added}")

        # Diagnostics + verify() read the UNCOMMITTED inserts through this same
        # connection. Nothing is committed until verify() passes, so any failed
        # check rolls the inserts back — fail-closed, never a partial write.
        for part_id in PART_IDS:
            grid = mrp.compute_mrp_grid(conn, part_id)
            rows = dict(grid["rows"])
            print(f"  {part_id}: on_hand={grid['on_hand_qty']} "
                  f"gross={sum(rows['Gross Requirements'])} "
                  f"planned_receipts={round(sum(rows['Planned Order Receipts']), 2)} "
                  f"min_PAB={round(min(rows['Projected Available Balance']), 2)}")

        verify(conn, as_of_before)
        conn.commit()
        print("Done. Weekly August 2026 demand applied for the top on-hand-value parts.")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
