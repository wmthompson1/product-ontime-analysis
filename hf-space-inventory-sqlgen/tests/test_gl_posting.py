"""
Gate-style test for the simple GL posting functions (gl_posting.py) and the
deterministic ledger backfill (migrations/backfill_gl_ledger.py).

Part A runs against a throwaway in-memory database (the gl_* DDL from
add_gl_ledger_tables.py) and proves each posting function's row shape,
balance semantics, idempotency, and fail-closed argument checks.

Part B runs read-only against the live manufacturing.db and proves the
backfilled ledger ties to the operational truth.

Run:  python tests/test_gl_posting.py
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "migrations"))

from gl_posting import (  # noqa: E402
    post_material_issue,
    post_labor,
    post_overhead,
    post_job_completion,
)
from add_gl_ledger_tables import DDL  # noqa: E402

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def balance(cur, table):
    return round(
        cur.execute(f"SELECT COALESCE(SUM(amount),0) FROM {table}").fetchone()[0], 2
    )


def part_a():
    print("Part A — posting functions on an in-memory ledger")
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(DDL)

    # Material: RM -amount, WIP +amount, MATERIAL detail.
    ev1 = post_material_issue(cur, "WO-1", "P-1", 100.0, "2026-01-05",
                              "material_issue", 1)
    check("material issue returns event id", ev1 is not None)
    check("RM balance -100", balance(cur, "gl_raw_materials_inventory") == -100.0)
    check("WIP balance +100", balance(cur, "gl_wip_inventory") == 100.0)
    check("MATERIAL detail row", cur.execute(
        "SELECT COUNT(*) FROM gl_job_cost_detail WHERE event_type='MATERIAL' "
        "AND job_id='WO-1' AND amount=100.0").fetchone()[0] == 1)

    # Labor + overhead into WIP.
    post_labor(cur, "WO-1", "P-1", 50.0, "2026-01-06 16:00:00", "labor_ticket", 7)
    post_overhead(cur, "WO-1", "P-1", 25.0, "2026-01-06 16:00:00", "labor_ticket", 7)
    check("WIP after labor+burden = 175", balance(cur, "gl_wip_inventory") == 175.0)
    check("LABOR and BURDEN detail rows", cur.execute(
        "SELECT COUNT(*) FROM gl_job_cost_detail "
        "WHERE event_type IN ('LABOR','BURDEN')").fetchone()[0] == 2)
    check("same source doc, two event types coexist", cur.execute(
        "SELECT COUNT(*) FROM gl_events WHERE source_table='labor_ticket' "
        "AND source_id='7'").fetchone()[0] == 2)

    # Completion: WIP -> FG for the full accumulated cost.
    post_job_completion(cur, "WO-1", "P-1", 175.0, "2026-01-20",
                        "work_order", "WO-1")
    check("WIP relieved to 0", balance(cur, "gl_wip_inventory") == 0.0)
    check("FG balance +175", balance(cur, "gl_finished_goods_inventory") == 175.0)

    # Idempotency: every replay is a no-op.
    before = cur.execute("SELECT COUNT(*) FROM gl_events").fetchone()[0]
    r1 = post_material_issue(cur, "WO-1", "P-1", 100.0, "2026-01-05",
                             "material_issue", 1)
    r2 = post_labor(cur, "WO-1", "P-1", 50.0, "2026-01-06 16:00:00",
                    "labor_ticket", 7)
    r3 = post_overhead(cur, "WO-1", "P-1", 25.0, "2026-01-06 16:00:00",
                       "labor_ticket", 7)
    r4 = post_job_completion(cur, "WO-1", "P-1", 175.0, "2026-01-20",
                             "work_order", "WO-1")
    after = cur.execute("SELECT COUNT(*) FROM gl_events").fetchone()[0]
    check("replays return None", (r1, r2, r3, r4) == (None, None, None, None))
    check("replays add no rows", before == after)

    # Fail-closed argument checks.
    for label, fn, args in (
        ("zero amount rejected", post_labor,
         ("WO-1", "P-1", 0.0, "2026-01-06", "labor_ticket", 8)),
        ("negative amount rejected", post_material_issue,
         ("WO-1", "P-1", -5.0, "2026-01-06", "material_issue", 9)),
        ("missing event_date rejected", post_overhead,
         ("WO-1", "P-1", 5.0, None, "labor_ticket", 10)),
    ):
        try:
            fn(cur, *args)
            check(label, False, "no ValueError raised")
        except ValueError:
            check(label, True)

    conn.close()


def part_b():
    print("Part B — backfilled ledger ties to operational truth (live DB)")
    if not os.path.exists(DB_PATH):
        print("  SKIP  live DB not found")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    n_events = cur.execute("SELECT COUNT(*) FROM gl_events").fetchone()[0]
    check("gl_events populated", n_events > 0, f"got {n_events}")

    # Per-job cost detail ties to work_order actuals to the cent.
    for element, col in (("MATERIAL", "act_mat_cost"),
                         ("LABOR", "act_lab_cost"),
                         ("BURDEN", "act_bur_cost")):
        drift = cur.execute(
            f"""
            SELECT COUNT(*) FROM work_order w
            LEFT JOIN (SELECT job_id, SUM(amount) s FROM gl_job_cost_detail
                       WHERE event_type=? GROUP BY job_id) d
              ON d.job_id = w.wo_id
            WHERE ABS(ROUND(w.{col},2) - ROUND(COALESCE(d.s,0),2)) >= 0.01
            """, (element,)).fetchone()[0]
        check(f"{element} detail ties to work_order.{col}", drift == 0,
              f"{drift} drifting WOs")

    # Completions only on closed, non-planned work orders.
    bad = cur.execute(
        "SELECT COUNT(*) FROM gl_events e JOIN work_order w ON w.wo_id=e.job_id "
        "WHERE e.event_type='FG_COMPLETION' AND "
        "(w.status != 'closed' OR w.wo_id LIKE 'WO-PLN-%')").fetchone()[0]
    check("no completions on planned/non-closed WOs", bad == 0, f"got {bad}")

    # Completion event dated at the WO close_date.
    mis = cur.execute(
        "SELECT COUNT(*) FROM gl_events e JOIN work_order w ON w.wo_id=e.job_id "
        "WHERE e.event_type='FG_COMPLETION' AND e.event_date != w.close_date"
    ).fetchone()[0]
    check("completions posted at close_date", mis == 0, f"{mis} mismatched")

    # Double-entry symmetry: every event's inventory lines are internally
    # consistent (WIP inflow events +, completion nets WIP -> FG).
    wip_in = cur.execute(
        "SELECT ROUND(COALESCE(SUM(amount),0),2) FROM gl_wip_inventory "
        "WHERE amount > 0").fetchone()[0]
    wip_out = cur.execute(
        "SELECT ROUND(COALESCE(-SUM(amount),0),2) FROM gl_wip_inventory "
        "WHERE amount < 0").fetchone()[0]
    fg = cur.execute(
        "SELECT ROUND(COALESCE(SUM(amount),0),2) FROM gl_finished_goods_inventory "
        "WHERE event_type = 'FG_COMPLETION'"
    ).fetchone()[0]
    check("WIP outflow equals FG completion inflow", wip_out == fg,
          f"wip_out={wip_out} fg={fg}")
    check("WIP balance is non-negative", round(wip_in - wip_out, 2) >= 0)

    # No wall-clock leakage: every ledger line's date matches its event's date.
    for t in ("gl_raw_materials_inventory", "gl_wip_inventory",
              "gl_finished_goods_inventory", "gl_job_cost_detail"):
        n = cur.execute(
            f"SELECT COUNT(*) FROM {t} l JOIN gl_events e ON e.event_id=l.event_id "
            "WHERE l.event_date != e.event_date").fetchone()[0]
        check(f"{t} dates match their events", n == 0, f"{n} mismatched")

    conn.close()


if __name__ == "__main__":
    part_a()
    part_b()
    print(f"\n{PASS} passed, {FAIL} failed")
    if FAIL:
        raise SystemExit(1)
    print("ALL CHECKS PASSED")
