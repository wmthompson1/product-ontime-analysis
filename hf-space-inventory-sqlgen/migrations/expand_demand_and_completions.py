"""Demand-side expansion: complete work orders, add customer-order demand,
plan more parts, and put finished goods on the shelf.

What it does (deterministic — no randomness; idempotent — safe to re-run):

1. WORK-ORDER COMPLETIONS — three long-open shop orders finish and close:
       WO-00007  P-10010  qty 1   closes 2026-01-14 (its required date)
       WO-00015  P-10024  qty 1   closes 2026-01-20 (early finish)
       WO-00009  P-10036  qty 5   closes 2026-01-21 (on the as-of date)
   Every close date is <= the current AS_OF (2026-01-21, from WO-00005), so
   AS_OF = MAX(work_order.close_date) NEVER moves and the MRP demo grid
   keeps its anchor. The MRP demo work orders (WO-MRP-*) are never touched.
   Work-order headers stay at 20 (band [10, 20]) — completions change
   status, not counts.

2. FINISHED GOODS — each completion receipts its build quantity to stock:
   part.on_hand_qty += work_order.quantity, applied ONLY on the run where
   the work order actually transitions to closed (that is what makes the
   increment idempotent).

3. COST/PROGRESS CASCADE — closing a work order changes the truth that the
   documented high-fidelity chain derives from, so this migration re-runs
   that exact chain (each member is a documented idempotent fixed point):
       backfill_operation_progress      -> all ops C + close dates
       backfill_operation_schedule      -> schedule chained to close dates
       backfill_supplier_rating_and_wo_actuals -> WO cost rollups at C-weight
       backfill_operation_actuals       -> op actuals reconcile to rollups
       backfill_labor_chain             -> ticket layer rebuilt to match

4. NEW CUSTOMER ORDERS — three new Open orders (headers 17 -> 20, at the
   top of the CO band [10, 20]; growth beyond this scales via LINES):
       CO-00016  Bell Textron          SITE-1
       CO-00017  Collins Aerospace     SITE-2
       CO-00018  Embraer Defense       SITE-3
   Their 20 lines cover the 20 MAKE parts that hold stock but had NO open
   demand inside the 9-month planning horizon — so every one of them
   becomes a planning part in the MRP dropdown (~104 -> ~124). Every part
   already carries on-hand inventory, so the fail-closed planning gate
   (positive lead time AND a real supply basis) holds by construction.
   Need-by dates are spread deterministically across horizon months +1..+7;
   desired release = need-by minus the part's lead time.

5. FAIL-CLOSED VERIFY — AS_OF unchanged, bands respected, the three work
   orders closed with every operation complete, labor/burden rollups
   reconcile op-for-op, and mrp_engine.validate_planning_inputs passes.
"""

import os
import sqlite3
import subprocess
import sys
from datetime import date, timedelta

HF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

sys.path.insert(0, HF_DIR)

# wo_id -> literal close date (all <= the seeded AS_OF, 2026-01-21).
WO_COMPLETIONS = {
    "WO-00007": "2026-01-14",
    "WO-00015": "2026-01-20",
    "WO-00009": "2026-01-21",
}

# Outside-service key repair: the accrual chain ties a service PO to its
# operation by (wo_id, service_id), but three legacy service POs carry the
# S-00x-coded service keys while their operations point at different service
# rows — so received service cost had no operation to land on (a latent
# rollup-vs-op drift the cascade re-run exposes). The PO records the service
# that was actually BOUGHT (cost recognized at receipt), so the operation is
# re-pointed at the PO's service. (wo_id, sequence_no) -> service_id.
OP_SERVICE_REPAIRS = {
    ("WO-00001", 190): "HEAT-TREAT",   # PO-SVC-001 (received, $1,080)
    ("WO-00002", 70): "ANODIZE-II",    # PO-SVC-002 (open, future receipt)
    ("WO-00003", 210): "NDT-UT",       # PO-SVC-003 (received, $1,170)
}

# The documented high-fidelity chain, in its mandatory order (idempotent).
CASCADE = [
    "backfill_operation_progress.py",
    "backfill_operation_schedule.py",
    "backfill_supplier_rating_and_wo_actuals.py",
    "backfill_operation_actuals.py",
    "backfill_labor_chain.py",
]

# order_id -> (customer, site, order_date)
NEW_ORDERS = {
    "CO-00016": ("Bell Textron", "SITE-1", "2026-01-08"),
    "CO-00017": ("Collins Aerospace", "SITE-2", "2026-01-12"),
    "CO-00018": ("Embraer Defense", "SITE-3", "2026-01-15"),
}

# order_id -> [(part_id, order_qty, need_by_month_offset), ...]
# The 20 MAKE parts with stock but no open in-horizon demand (probed
# 2026-07-06); quantities sized so most lines exceed on-hand and force
# planned orders in the grid. Month offset is months after the as-of month.
NEW_LINES = {
    "CO-00016": [
        ("P-10011", 30.0, 1),
        ("P-10012", 25.0, 2),
        ("P-10024", 50.0, 3),
        ("P-10025", 90.0, 4),
        ("P-10026", 12.0, 5),
        ("PN-10010", 250.0, 6),
        ("PN-10030", 120.0, 7),
    ],
    "CO-00017": [
        ("PN-10040", 60.0, 1),
        ("PN-10050", 25.0, 2),
        ("PN-10060", 150.0, 3),
        ("PN-10070", 80.0, 4),
        ("PN-10080", 45.0, 5),
        ("PN-10090", 120.0, 6),
        ("PN-10100", 30.0, 7),
    ],
    "CO-00018": [
        ("PN-10140", 20.0, 1),
        ("PN-10150", 110.0, 2),
        ("PN-10160", 120.0, 3),
        ("PN-10170", 15.0, 4),
        ("PN-10190", 95.0, 5),
        ("PN-10200", 50.0, 6),
    ],
}

PRICE_MARKUP = 1.35  # sell price = unit_cost * markup, rounded to cents


def add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 15)  # mid-month need-by, always inside the bucket


def repair_op_service_keys(cur):
    repaired = 0
    for (wo_id, seq), service_id in OP_SERVICE_REPAIRS.items():
        if not cur.execute(
            "SELECT 1 FROM service WHERE service_id=?", (service_id,)
        ).fetchone():
            raise SystemExit(f"FAIL-CLOSED: service {service_id} not found")
        cur.execute(
            "UPDATE operation SET service_id=? "
            "WHERE wo_id=? AND sequence_no=? AND service_id IS NOT NULL "
            "AND service_id<>?",
            (service_id, wo_id, seq, service_id),
        )
        repaired += cur.rowcount
    return repaired


def complete_work_orders(cur):
    closed_now = []
    for wo_id, close_dt in WO_COMPLETIONS.items():
        row = cur.execute(
            "SELECT status, part_id, quantity FROM work_order WHERE wo_id=?",
            (wo_id,),
        ).fetchone()
        if not row:
            raise SystemExit(f"FAIL-CLOSED: work order {wo_id} not found")
        status, part_id, qty = row
        if status == "closed":
            continue  # already done on a prior run
        cur.execute(
            "UPDATE work_order SET status='closed', close_date=? WHERE wo_id=?",
            (close_dt, wo_id),
        )
        # finished goods to stock — only on the transitioning run
        cur.execute(
            "UPDATE part SET on_hand_qty = on_hand_qty + ? WHERE part_id=?",
            (qty, part_id),
        )
        closed_now.append((wo_id, part_id, qty))
    return closed_now


def run_cascade():
    for name in CASCADE:
        path = os.path.join(HF_DIR, "migrations", name)
        r = subprocess.run([sys.executable, path], cwd=HF_DIR,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            raise SystemExit(f"FAIL-CLOSED: cascade step {name} failed")
        print(f"  cascade: {name} OK")


def insert_customer_orders(cur, as_of):
    added_headers = 0
    added_lines = 0
    for order_id, (customer, site, order_date) in NEW_ORDERS.items():
        cur.execute(
            "INSERT OR IGNORE INTO customer_order "
            "(order_id, customer_name, order_date, site_id, status) "
            "VALUES (?,?,?,?, 'Open')",
            (order_id, customer, order_date, site),
        )
        added_headers += cur.rowcount
        for line_no, (part_id, qty, offset) in enumerate(NEW_LINES[order_id], 1):
            if cur.execute(
                "SELECT 1 FROM customer_order_line WHERE order_id=? AND line_no=?",
                (order_id, line_no),
            ).fetchone():
                continue
            prow = cur.execute(
                "SELECT unit_cost, lead_time_days FROM part WHERE part_id=?",
                (part_id,),
            ).fetchone()
            if not prow:
                raise SystemExit(f"FAIL-CLOSED: part {part_id} not found for {order_id}")
            unit_cost, lead = prow
            need_by = add_months(as_of, offset)
            release = need_by - timedelta(days=int(lead or 0))
            cur.execute(
                "INSERT INTO customer_order_line "
                "(order_id, line_no, part_id, site_id, order_qty, unit_price, "
                " need_by_date, desired_release_date) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (order_id, line_no, part_id, NEW_ORDERS[order_id][1], qty,
                 round((unit_cost or 0) * PRICE_MARKUP, 2),
                 need_by.isoformat(), release.isoformat()),
            )
            added_lines += 1
    return added_headers, added_lines


def verify(conn, as_of_before):
    import mrp_engine as mrp

    cur = conn.cursor()
    errors = []

    as_of_after = mrp.compute_as_of(conn)
    if as_of_after != as_of_before:
        errors.append(f"AS_OF moved: {as_of_before} -> {as_of_after}")

    wo_n = cur.execute("SELECT COUNT(*) FROM work_order").fetchone()[0]
    co_n = cur.execute("SELECT COUNT(*) FROM customer_order").fetchone()[0]
    if not (10 <= wo_n <= 20):
        errors.append(f"work-order headers out of band: {wo_n}")
    if not (10 <= co_n <= 20):
        errors.append(f"customer-order headers out of band: {co_n}")

    for wo_id in WO_COMPLETIONS:
        st = cur.execute(
            "SELECT status FROM work_order WHERE wo_id=?", (wo_id,)
        ).fetchone()
        if not st or st[0] != "closed":
            errors.append(f"{wo_id} not closed")
        open_ops = cur.execute(
            "SELECT COUNT(*) FROM operation WHERE wo_id=? "
            "AND (status<>'C' OR close_date IS NULL)", (wo_id,)
        ).fetchone()[0]
        if open_ops:
            errors.append(f"{wo_id}: {open_ops} operation(s) not complete")

    # WO rollups reconcile with operation actuals to the cent.
    drift = cur.execute("""
        SELECT COUNT(*) FROM work_order w
        WHERE ABS(COALESCE(w.act_lab_cost,0) + COALESCE(w.act_bur_cost,0)
                  + COALESCE(w.act_ser_cost,0)
              - (SELECT COALESCE(SUM(o.act_atl_lab_cost + o.act_atl_bur_cost
                                     + o.act_atl_ser_cost), 0)
                 FROM operation o WHERE o.wo_id = w.wo_id)) > 0.01
    """).fetchone()[0]
    if drift:
        errors.append(f"{drift} work order(s) with op-actuals drift")

    for order_id, lines in NEW_LINES.items():
        n = cur.execute(
            "SELECT COUNT(*) FROM customer_order_line WHERE order_id=?",
            (order_id,),
        ).fetchone()[0]
        if n != len(lines):
            errors.append(f"{order_id}: expected {len(lines)} lines, found {n}")

    protected = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE wo_id LIKE 'WO-MRP-%' "
        "AND status='closed'"
    ).fetchone()[0]
    if protected:
        errors.append(f"{protected} MRP demo work order(s) were closed")

    try:
        summary = mrp.validate_planning_inputs(conn)
        print(f"  verify: MRP planning gate OK — {summary['demand_parts']} "
              "planning parts")
    except ValueError as exc:
        errors.append(f"MRP planning gate failed: {exc}")

    if errors:
        for e in errors:
            print(f"  VERIFY FAIL: {e}")
        raise SystemExit("FAIL-CLOSED: demand expansion verification failed")
    print("  verify: all demand-expansion invariants hold")


def run():
    import mrp_engine as mrp

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    as_of_before = mrp.compute_as_of(conn)
    print(f"  AS_OF = {as_of_before}")

    repaired = repair_op_service_keys(cur)
    print(f"  outside-service key repairs: {repaired} operation(s)")

    closed = complete_work_orders(cur)
    for wo_id, part_id, qty in closed:
        print(f"  completed {wo_id}: +{qty} {part_id} to stock")
    if not closed:
        print("  completions: none (already closed)")
    conn.commit()  # cascade subprocesses must see the closes/repairs

    # ALWAYS re-run the cascade: every step is a documented idempotent fixed
    # point, so this is cheap on a clean rerun — and it is what makes a rerun
    # self-healing if a previous invocation died after the commit above but
    # before (or during) the cascade.
    run_cascade()

    headers, lines = insert_customer_orders(cur, as_of_before)
    print(f"  customer orders: +{headers} header(s), +{lines} line(s)")

    verify(conn, as_of_before)
    conn.commit()
    conn.close()
    print("Done. Demand expansion complete.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
