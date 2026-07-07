"""Synthetic demand so planned orders visibly net against on-hand — fail-closed.

Why: the prior completion migrations receipted finished goods to stock for a
handful of parts (synthetic SUPPLY). To prove the MRP nets that supply, those
parts need open demand that exceeds on-hand, so the grid draws the projected
available balance down to safety stock and then plans the remaining shortfall.

What it does (deterministic — no randomness; idempotent — safe to re-run):

1. DEMAND LINES — adds customer-order demand lines to an existing OPEN order
   (CO-MRP-001, the purpose-built MRP demand order — attaching here avoids the
   frozen line counts on CO-00016/17/18 and the "forecast == unlinked-WO parts"
   lock on the forecast table) for the two parts whose on-hand was boosted by
   the last-week completions. Quantities are sized above on-hand so a planned
   order is forced AFTER on-hand is consumed:
       P-10024  +60  need_by 2026-02-15   (on-hand 48  -> drawn to safety)
       P-10025  +60  need_by 2026-02-15   (on-hand ~87 -> drawn to safety)
   Growth is via LINES on an existing header — customer-order headers stay in
   the demo band [10, 20] and AS_OF (2026-01-21) never moves. need_by dates sit
   inside the 9-month planning horizon; desired_release = need_by - lead time.

2. FAIL-CLOSED VERIFY — for every targeted part the recomputed MRP grid must:
     * generate Planned Order Receipts > 0 (a real shortfall exists), and
     * draw the Projected Available Balance below the starting on-hand (on-hand
       is actually subtracted, never ignored), never below safety stock.
   Also: AS_OF unchanged, customer-order header band [10, 20] intact, and
   mrp_engine.validate_planning_inputs still passes.
"""

import os
import sqlite3
import sys
from datetime import date, timedelta

HF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

sys.path.insert(0, HF_DIR)

PRICE_MARKUP = 1.35  # sell price = unit_cost * markup (matches expand migration)

# (order_id, part_id, order_qty, need_by ISO). The order must already be Open.
DEMAND_LINES = [
    ("CO-MRP-001", "P-10024", 60.0, "2026-02-15"),
    ("CO-MRP-001", "P-10025", 60.0, "2026-02-15"),
]


def _next_line_no(cur, order_id):
    row = cur.execute(
        "SELECT COALESCE(MAX(line_no), 0) FROM customer_order_line WHERE order_id=?",
        (order_id,),
    ).fetchone()
    return (row[0] or 0) + 1


def add_demand(cur):
    added = 0
    for order_id, part_id, qty, need_by in DEMAND_LINES:
        order = cur.execute(
            "SELECT status, site_id FROM customer_order WHERE order_id=?",
            (order_id,),
        ).fetchone()
        if not order:
            raise SystemExit(f"FAIL-CLOSED: customer order {order_id} not found")
        if order[0] != "Open":
            raise SystemExit(
                f"FAIL-CLOSED: {order_id} is '{order[0]}', demand must attach to an Open order"
            )
        site_id = order[1]

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
            (order_id, part_id, need_by, qty),
        ).fetchone():
            continue

        release = date.fromisoformat(need_by) - timedelta(days=int(lead or 0))
        cur.execute(
            "INSERT INTO customer_order_line "
            "(order_id, line_no, part_id, site_id, order_qty, unit_price, "
            " need_by_date, desired_release_date) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (order_id, _next_line_no(cur, order_id), part_id, site_id, qty,
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

    co_n = cur.execute("SELECT COUNT(*) FROM customer_order").fetchone()[0]
    if not (10 <= co_n <= 20):
        errors.append(f"customer-order headers out of band: {co_n}")

    for order_id, part_id, qty, need_by in DEMAND_LINES:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM customer_order_line "
            "WHERE order_id=? AND part_id=? AND need_by_date=? AND order_qty=?",
            (order_id, part_id, need_by, qty),
        ).fetchone()[0]
        if cnt != 1:
            errors.append(
                f"{part_id}: expected exactly 1 demand line on {order_id}, found {cnt}"
            )

        grid = mrp.compute_mrp_grid(conn, part_id)
        rows = dict(grid["rows"])
        on_hand = grid["on_hand_qty"] or 0
        receipts = sum(rows["Planned Order Receipts"])
        pab = rows["Projected Available Balance"]
        safety = grid["safety_stock"]
        if receipts <= 0:
            errors.append(f"{part_id}: no planned order receipts (demand did not exceed supply)")
        if not (min(pab) < on_hand):
            errors.append(f"{part_id}: on-hand not drawn down (min PAB {min(pab)} >= on_hand {on_hand})")
        if min(pab) < safety - 1e-6:
            errors.append(f"{part_id}: projected balance {min(pab)} fell below safety stock {safety}")

    try:
        summary = mrp.validate_planning_inputs(conn)
        print(f"  verify: MRP planning gate OK — {summary['demand_parts']} planning parts")
    except ValueError as exc:
        errors.append(f"MRP planning gate failed: {exc}")

    if errors:
        for e in errors:
            print(f"  VERIFY FAIL: {e}")
        raise SystemExit("FAIL-CLOSED: synthetic-demand verification failed")
    print("  verify: on-hand is netted and planned orders cover the shortfall")


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
        for _order_id, part_id, _qty, _need_by in DEMAND_LINES:
            grid = mrp.compute_mrp_grid(conn, part_id)
            rows = dict(grid["rows"])
            print(f"  {part_id}: on_hand={grid['on_hand_qty']} "
                  f"gross={sum(rows['Gross Requirements'])} "
                  f"planned_receipts={round(sum(rows['Planned Order Receipts']), 2)} "
                  f"min_PAB={round(min(rows['Projected Available Balance']), 2)}")

        verify(conn, as_of_before)
        conn.commit()
        print("Done. Synthetic demand applied; planned orders net against on-hand.")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
