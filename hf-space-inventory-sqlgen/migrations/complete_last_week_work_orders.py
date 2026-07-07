"""Last-week work-order completions — deterministic, idempotent, fail-closed.

What it does (no randomness; safe to re-run):

1. WORK-ORDER COMPLETIONS — three in-progress shop orders finish inside the
   dataset's latest week (the 7 days ending on the as-of date, 2026-01-21):
       WO-00003  P-10024  qty 4    closes 2026-01-16 (early finish)
       WO-00008  P-10025  qty 2    closes 2026-01-19 (firmed lot completes)
       WO-00010  P-10024  qty 2    closes 2026-01-21 (long-open order finishes)
   Every close date is <= the current AS_OF (2026-01-21), so
   AS_OF = MAX(work_order.close_date) NEVER moves and the MRP demo grid keeps
   its anchor. Work-order headers stay at 20 (band [10, 20]) — completions
   change status, not counts. The MRP demo work orders (WO-MRP-*) and the
   two unreleased shop orders (never released to the floor) are untouched.

2. FINISHED GOODS — each completion receipts its build quantity to stock:
   part.on_hand_qty += work_order.quantity, applied ONLY on the run where the
   work order actually transitions to closed (that is what makes the increment
   idempotent). This is the synthetic supply that planned orders match against.

3. COST/PROGRESS CASCADE — closing a work order changes the truth the
   high-fidelity chain derives from, so this migration re-runs that exact
   chain (each member is a documented idempotent fixed point):
       backfill_operation_progress      -> all ops C + close dates
       backfill_operation_schedule      -> schedule chained to close dates
       backfill_supplier_rating_and_wo_actuals -> WO cost rollups at C-weight
       backfill_operation_actuals       -> op actuals reconcile to rollups
       backfill_labor_chain             -> ticket layer rebuilt to match

4. FAIL-CLOSED VERIFY — AS_OF unchanged, header bands respected, the three
   work orders closed with every operation complete, labor/burden rollups
   reconcile op-for-op, no MRP demo order closed, and
   mrp_engine.validate_planning_inputs passes.
"""

import os
import sqlite3
import subprocess
import sys
from datetime import date

HF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

sys.path.insert(0, HF_DIR)

# The 7-day window ending on the as-of date (inclusive). Completions must land
# inside it AND be <= AS_OF so the anchor never moves.
WEEK_START = date(2026, 1, 15)
WEEK_END = date(2026, 1, 21)  # == seeded AS_OF

# wo_id -> literal close date (all inside [WEEK_START, WEEK_END]).
WO_COMPLETIONS = {
    "WO-00003": "2026-01-16",
    "WO-00008": "2026-01-19",
    "WO-00010": "2026-01-21",
}

# The documented high-fidelity chain, in its mandatory order (idempotent).
CASCADE = [
    "backfill_operation_progress.py",
    "backfill_operation_schedule.py",
    "backfill_supplier_rating_and_wo_actuals.py",
    "backfill_operation_actuals.py",
    "backfill_labor_chain.py",
]


def _check_window(as_of_before):
    """Fail closed if any completion date is outside the last-week window or
    would move the anchor forward."""
    for wo_id, close_dt in WO_COMPLETIONS.items():
        d = date.fromisoformat(close_dt)
        if not (WEEK_START <= d <= WEEK_END):
            raise SystemExit(
                f"FAIL-CLOSED: {wo_id} close {close_dt} outside last-week "
                f"window [{WEEK_START}, {WEEK_END}]"
            )
        as_of_date = as_of_before
        if isinstance(as_of_date, str):
            as_of_date = date.fromisoformat(as_of_date)
        if as_of_date and d > as_of_date:
            raise SystemExit(
                f"FAIL-CLOSED: {wo_id} close {close_dt} would move AS_OF past "
                f"{as_of_before}"
            )


def complete_work_orders(cur):
    closed_now = []
    for wo_id, close_dt in WO_COMPLETIONS.items():
        row = cur.execute(
            "SELECT status, part_id, quantity FROM work_order WHERE wo_id=?",
            (wo_id,),
        ).fetchone()
        if not row:
            raise SystemExit(f"FAIL-CLOSED: work order {wo_id} not found")
        if wo_id.startswith("WO-MRP-"):
            raise SystemExit(f"FAIL-CLOSED: refusing to close MRP demo order {wo_id}")
        status, part_id, qty = row
        if status == "closed":
            continue  # already done on a prior run
        if status not in ("released", "firmed"):
            raise SystemExit(
                f"FAIL-CLOSED: {wo_id} is '{status}', not a floor-released order "
                "(only released/firmed work orders may be completed)"
            )
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


def verify(conn, as_of_before):
    import mrp_engine as mrp

    cur = conn.cursor()
    errors = []

    as_of_after = mrp.compute_as_of(conn)
    if as_of_after != as_of_before:
        errors.append(f"AS_OF moved: {as_of_before} -> {as_of_after}")

    wo_n = cur.execute("SELECT COUNT(*) FROM work_order").fetchone()[0]
    if not (10 <= wo_n <= 20):
        errors.append(f"work-order headers out of band: {wo_n}")

    for wo_id, close_dt in WO_COMPLETIONS.items():
        row = cur.execute(
            "SELECT status, close_date FROM work_order WHERE wo_id=?", (wo_id,)
        ).fetchone()
        if not row or row[0] != "closed":
            errors.append(f"{wo_id} not closed")
        elif row[1] != close_dt:
            errors.append(f"{wo_id} close_date {row[1]} != {close_dt}")
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
        raise SystemExit("FAIL-CLOSED: last-week completion verification failed")
    print("  verify: all last-week completion invariants hold")


def run():
    import mrp_engine as mrp

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    as_of_before = mrp.compute_as_of(conn)
    print(f"  AS_OF = {as_of_before}")

    _check_window(as_of_before)

    closed = complete_work_orders(cur)
    for wo_id, part_id, qty in closed:
        print(f"  completed {wo_id}: +{qty} {part_id} to stock")
    if not closed:
        print("  completions: none (already closed)")
    conn.commit()  # cascade subprocesses must see the closes

    # ALWAYS re-run the cascade: every step is a documented idempotent fixed
    # point, so this is cheap on a clean rerun — and it makes a rerun
    # self-healing if a previous invocation died after the commit above but
    # before (or during) the cascade.
    run_cascade()

    verify(conn, as_of_before)
    conn.commit()
    conn.close()
    print("Done. Last-week completions applied.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
