"""Ship the first weekly August bucket early — full ledger event, 2026-07-23.

Business story: the customer pulled in the first weekly bucket of the August
demand series (migrations/seed_august_weekly_demand.py), so one week's worth
of finished goods ships on 2026-07-23 — before the AS_OF anchor (2026-07-31),
after the June close (2026-06-30). Everything is deterministic and dated from
the shipment, never wall-clock.

What it does (idempotent — safe to re-run; fail-closed — nothing commits
unless every check holds):

1. SCHEMA — adds ``shipped_qty`` / ``shipped_date`` to customer_order_line
   (same precedent as need_by_date / desired_release_date). mrp_engine
   subtracts shipped quantity from open demand once the columns exist.

2. PHYSICAL SHIPMENT — the three 2026-08-07 lines on CO-MRP-002 ship in
   full (P-10037 24, P-10014 24, P-10024 18):
     * line marked shipped (shipped_qty = order_qty, shipped_date),
     * an Issue/Out inventory_transaction per line,
     * part.on_hand_qty decremented — transition-guarded, applied only
       when a line flips from unshipped to shipped, so re-runs never
       double-decrement.

3. LEDGER EVENT (CUSTOMER_SHIPMENT) — cost leaves Finished Goods honestly:
     * P-10024 (MAKE): FG holds the accumulated cost of its four closed
       jobs (11 units). Each job's FG_COMPLETION inflow is relieved IN FULL
       by one CUSTOMER_SHIPMENT event — every ledger event still costs
       exactly one job (:forJob) — leaving the part's FG net at $0. The
       7 remaining shipped units come from purchased/legacy stock the
       job-costing ledger never capitalized.
     * P-10037 / P-10014 (BUY): never job-completed, so FG holds $0 for
       them — a physical-only shipment. The ledger does not invent cost
       that was never posted in (honest boundary, stated loudly below).

4. FAIL-CLOSED VERIFY — lines shipped exactly once, on-hand literals match,
   P-10024 FG nets to $0 per job and in total, no job's FG goes negative,
   WIP untouched, June month-end FG balance unchanged, AS_OF unchanged,
   header bands untouched, and the MRP planning gate still passes with the
   shipped quantities excluded from open demand.
"""

import os
import sqlite3
import sys

HF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

sys.path.insert(0, HF_DIR)

SHIP_DATE = "2026-07-23"
ORDER_ID = "CO-MRP-002"
NEED_BY = "2026-08-07"  # the first weekly August bucket ships early

# (part_id, qty) — baked literals mirroring seed_august_weekly_demand.py.
SHIP_LINES = [
    ("P-10037", 24.0),
    ("P-10014", 24.0),
    ("P-10024", 18.0),
]

# Expected on-hand AFTER shipment (baked: 61.6-24, 62.4-24, 48-18).
EXPECTED_ON_HAND = {"P-10037": 37.6, "P-10014": 38.4, "P-10024": 30.0}

CENT = 0.01
JUNE_CUTOFF = "2026-06-30"


def _has_column(cur, table, column):
    return any(r[1] == column for r in cur.execute(f"PRAGMA table_info({table})"))


def add_columns(cur):
    added = 0
    if not _has_column(cur, "customer_order_line", "shipped_qty"):
        cur.execute(
            "ALTER TABLE customer_order_line ADD COLUMN shipped_qty REAL DEFAULT 0"
        )
        added += 1
    if not _has_column(cur, "customer_order_line", "shipped_date"):
        cur.execute("ALTER TABLE customer_order_line ADD COLUMN shipped_date DATE")
        added += 1
    return added


def _line_row(cur, part_id, qty):
    row = cur.execute(
        "SELECT order_line_id, site_id, COALESCE(shipped_qty, 0) "
        "FROM customer_order_line "
        "WHERE order_id=? AND part_id=? AND order_qty=? AND date(need_by_date)=?",
        (ORDER_ID, part_id, qty, NEED_BY),
    ).fetchall()
    if len(row) != 1:
        raise SystemExit(
            f"FAIL-CLOSED: expected exactly 1 {NEED_BY} line for {part_id} "
            f"on {ORDER_ID}, found {len(row)} — run seed_august_weekly_demand first"
        )
    return row[0]


def ship_lines(cur):
    """Mark lines shipped; move stock; return the line ids (transition-aware)."""
    shipped_now = []
    line_ids = {}
    for part_id, qty in SHIP_LINES:
        line_id, site_id, already = _line_row(cur, part_id, qty)
        line_ids[part_id] = line_id
        if already > 0:
            if abs(already - qty) > 1e-9:
                raise SystemExit(
                    f"FAIL-CLOSED: {part_id} line {line_id} partially shipped "
                    f"({already} of {qty}) — unexpected state"
                )
            continue  # already shipped by a previous run — no physical re-move
        cur.execute(
            "UPDATE customer_order_line SET shipped_qty=?, shipped_date=? "
            "WHERE order_line_id=?",
            (qty, SHIP_DATE, line_id),
        )
        cur.execute(
            "INSERT INTO inventory_transaction "
            "(class, type, part_id, site_id, quantity, trans_date) "
            "VALUES ('I','O',?,?,?,?)",
            (part_id, site_id, qty, SHIP_DATE),
        )
        cur.execute(
            "UPDATE part SET on_hand_qty = on_hand_qty - ? WHERE part_id=?",
            (qty, part_id),
        )
        shipped_now.append(part_id)
    return shipped_now, line_ids


def post_ledger(cur, line_ids):
    """Relieve P-10024's four closed jobs' FG cost in full (CUSTOMER_SHIPMENT).

    Idempotent via gl_posting's (source_table, source_id, event_type) key.
    BUY parts P-10037/P-10014 hold $0 in FG (never job-completed): physical-
    only shipment for them — the ledger never invents cost.
    """
    from gl_posting import post_customer_shipment

    part_id = "P-10024"
    inflows = cur.execute(
        """
        SELECT f.job_id, ROUND(SUM(f.amount), 2)
        FROM gl_finished_goods_inventory f
        JOIN work_order w ON w.wo_id = f.job_id
        WHERE w.part_id = ? AND f.event_type = 'FG_COMPLETION'
        GROUP BY f.job_id ORDER BY f.job_id
        """,
        (part_id,),
    ).fetchall()
    if not inflows:
        raise SystemExit(f"FAIL-CLOSED: no FG_COMPLETION inflows for {part_id}")

    posted = 0
    for job_id, amount in inflows:
        ev = post_customer_shipment(
            cur, job_id, part_id, amount, SHIP_DATE,
            "customer_order_line", f"{line_ids[part_id]}:{job_id}",
        )
        if ev is not None:
            posted += 1
    return posted


def verify(conn, as_of_before, june_fg_before):
    import mrp_engine as mrp

    cur = conn.cursor()
    errors = []

    if mrp.compute_as_of(conn) != as_of_before:
        errors.append(f"AS_OF moved from {as_of_before}")

    for part_id, qty in SHIP_LINES:
        row = cur.execute(
            "SELECT shipped_qty, shipped_date FROM customer_order_line "
            "WHERE order_id=? AND part_id=? AND order_qty=? AND date(need_by_date)=?",
            (ORDER_ID, part_id, qty, NEED_BY),
        ).fetchone()
        if not row or abs((row[0] or 0) - qty) > 1e-9 or row[1] != SHIP_DATE:
            errors.append(f"{part_id}: line not shipped as expected ({row})")
        on_hand = cur.execute(
            "SELECT on_hand_qty FROM part WHERE part_id=?", (part_id,)
        ).fetchone()[0]
        if abs(on_hand - EXPECTED_ON_HAND[part_id]) > 1e-6:
            errors.append(
                f"{part_id}: on_hand {on_hand} != expected {EXPECTED_ON_HAND[part_id]}"
            )

    # Ledger: P-10024 FG fully relieved, per job and in total; nothing negative.
    bad_jobs = cur.execute(
        """
        SELECT f.job_id, ROUND(SUM(f.amount), 2)
        FROM gl_finished_goods_inventory f
        JOIN work_order w ON w.wo_id = f.job_id
        WHERE w.part_id = 'P-10024'
        GROUP BY f.job_id HAVING ABS(SUM(f.amount)) > ?
        """,
        (CENT,),
    ).fetchall()
    if bad_jobs:
        errors.append(f"P-10024 FG not fully relieved per job: {bad_jobs}")
    negative = cur.execute(
        "SELECT job_id, ROUND(SUM(amount),2) FROM gl_finished_goods_inventory "
        "GROUP BY job_id HAVING SUM(amount) < -?",
        (CENT,),
    ).fetchall()
    if negative:
        errors.append(f"FG net negative for job(s): {negative}")
    wip_touched = cur.execute(
        "SELECT COUNT(*) FROM gl_wip_inventory WHERE event_type='CUSTOMER_SHIPMENT'"
    ).fetchone()[0]
    if wip_touched:
        errors.append("CUSTOMER_SHIPMENT wrote WIP lines (must not)")

    # June close is history: FG balance as of 2026-06-30 must be untouched.
    june_fg = cur.execute(
        "SELECT ROUND(COALESCE(SUM(amount),0),2) FROM gl_finished_goods_inventory "
        "WHERE date(event_date) <= ?",
        (JUNE_CUTOFF,),
    ).fetchone()[0]
    if abs(june_fg - june_fg_before) > CENT:
        errors.append(f"June month-end FG moved: {june_fg_before} -> {june_fg}")

    co_n = cur.execute(
        "SELECT COUNT(*) FROM customer_order WHERE order_id NOT LIKE 'CO-JUL-%'"
    ).fetchone()[0]
    if not (10 <= co_n <= 20):
        errors.append(f"customer-order headers out of band: {co_n}")

    # MRP: shipped quantity is out of open demand; the gate still passes.
    for part_id, qty in SHIP_LINES:
        grid = mrp.compute_mrp_grid(conn, part_id)
        rows = dict(grid["rows"])
        if min(rows["Projected Available Balance"]) < grid["safety_stock"] - 1e-6:
            errors.append(f"{part_id}: projected balance fell below safety stock")
    try:
        summary = mrp.validate_planning_inputs(conn)
        print(f"  verify: MRP planning gate OK — {summary['demand_parts']} planning parts")
    except ValueError as exc:
        errors.append(f"MRP planning gate failed: {exc}")

    if errors:
        for e in errors:
            print(f"  VERIFY FAIL: {e}")
        raise SystemExit("FAIL-CLOSED: first-bucket shipment verification failed")
    print("  verify: first August bucket shipped — stock, demand, and ledger agree")


def run():
    import mrp_engine as mrp

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        as_of_before = mrp.compute_as_of(conn)
        june_fg_before = cur.execute(
            "SELECT ROUND(COALESCE(SUM(amount),0),2) FROM gl_finished_goods_inventory "
            "WHERE date(event_date) <= ?",
            (JUNE_CUTOFF,),
        ).fetchone()[0]
        print(f"  AS_OF = {as_of_before}; June FG = {june_fg_before}")

        n_cols = add_columns(cur)
        print(f"  shipped_qty/shipped_date columns added: {n_cols}")

        shipped_now, line_ids = ship_lines(cur)
        print(f"  lines shipped this run: {shipped_now or '(already shipped)'}")

        posted = post_ledger(cur, line_ids)
        print(f"  CUSTOMER_SHIPMENT events posted this run: {posted}")
        print("  NOTE: P-10037/P-10014 are BUY parts with $0 in FG — physical-only "
              "shipment (the ledger never invents cost that was never posted in)")

        # verify() reads the UNCOMMITTED writes through this same connection;
        # nothing commits unless every check holds — fail-closed.
        verify(conn, as_of_before, june_fg_before)
        conn.commit()
        print("  committed: first weekly August bucket shipped on 2026-07-23")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
