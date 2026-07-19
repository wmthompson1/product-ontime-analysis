"""Gate test — read-only month-end WIP reconciliation (as of 2026-06-30).

Option A per user decision: NO period-close semantics, NO new posting logic,
NO synthetic month-end entries.  This test only *reads* the existing GL
ledger (gl_events / gl_wip_inventory / gl_raw_materials_inventory /
gl_finished_goods_inventory) filtered to event_date <= AS_OF and proves the
month-end position ties, cent-exact, to the source documents:

  - WIP balance as of month end == inflows through the date
    (material_issue.total_cost + labor_ticket.labor_cost/burden_cost, taken
    as-is, never recomputed) minus completion outflows for jobs closed by
    the date;
  - every job closed on or before AS_OF carries zero WIP as of AS_OF;
  - every job still open at AS_OF carries WIP equal to its accumulated
    inflows through AS_OF;
  - RM outflow through AS_OF == material_issue total through AS_OF;
  - FG balance through AS_OF == sum of accumulated job cost for jobs closed
    on or before AS_OF (COGS out of scope — nothing leaves FG);
  - guard: the window is non-trivial (events exist on or before AS_OF), so
    the test can never pass vacuously on an empty slice.

All dates are data-derived (event_date from source documents, close_date
from work_order) — never wall-clock.

Run gate-style:
    cd hf-space-inventory-sqlgen
    python tests/test_month_end_wip_reconciliation.py
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

AS_OF = "2026-06-30"
CENT = 0.005

FAILURES = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print(f"Month-end reconciliation as of {AS_OF} (read-only)")

    # 0 — guard: non-vacuous window
    n_events = cur.execute(
        "SELECT COUNT(*) FROM gl_events WHERE DATE(event_date) <= ?", (AS_OF,)
    ).fetchone()[0]
    check("window is non-trivial (GL events exist on or before AS_OF)",
          n_events > 0, str(n_events))

    # 1 — ledger-side month-end balances
    wip_bal = cur.execute(
        "SELECT COALESCE(ROUND(SUM(amount),2),0) FROM gl_wip_inventory "
        "WHERE DATE(event_date) <= ?", (AS_OF,)
    ).fetchone()[0]
    rm_out = cur.execute(
        "SELECT COALESCE(ROUND(-SUM(amount),2),0) FROM gl_raw_materials_inventory "
        "WHERE amount < 0 AND DATE(event_date) <= ?", (AS_OF,)
    ).fetchone()[0]
    fg_bal = cur.execute(
        "SELECT COALESCE(ROUND(SUM(amount),2),0) FROM gl_finished_goods_inventory "
        "WHERE DATE(event_date) <= ?", (AS_OF,)
    ).fetchone()[0]

    # 2 — independent source-document expectation (as-is, never recomputed)
    mi_thru = cur.execute(
        "SELECT COALESCE(ROUND(SUM(total_cost),2),0) FROM material_issue "
        "WHERE DATE(issue_date) <= ?", (AS_OF,)
    ).fetchone()[0]
    lab_thru, bur_thru = cur.execute(
        "SELECT COALESCE(ROUND(SUM(labor_cost),2),0), "
        "       COALESCE(ROUND(SUM(burden_cost),2),0) "
        "FROM labor_ticket WHERE DATE(clock_out) <= ?", (AS_OF,)
    ).fetchone()
    closed_cost_thru = cur.execute(
        "SELECT COALESCE(ROUND(SUM(act_mat_cost + act_lab_cost + act_bur_cost),2),0) "
        "FROM work_order WHERE status = 'closed' AND DATE(close_date) <= ?",
        (AS_OF,)
    ).fetchone()[0]

    expected_wip = round(mi_thru + lab_thru + bur_thru - closed_cost_thru, 2)
    check("month-end WIP == source inflows minus completions (cent-exact)",
          abs(wip_bal - expected_wip) <= CENT,
          f"ledger {wip_bal} vs expected {expected_wip} "
          f"(mi {mi_thru} + lab {lab_thru} + bur {bur_thru} - closed {closed_cost_thru})")

    check("month-end RM outflow == material_issue total through AS_OF",
          abs(rm_out - mi_thru) <= CENT, f"{rm_out} vs {mi_thru}")

    check("month-end FG balance == accumulated cost of jobs closed by AS_OF",
          abs(fg_bal - closed_cost_thru) <= CENT,
          f"{fg_bal} vs {closed_cost_thru}")

    # 3 — per-job: closed-by-month-end jobs net to zero WIP as of AS_OF
    bad_closed = cur.execute(
        """
        SELECT w.job_id, ROUND(SUM(w.amount),2) FROM gl_wip_inventory w
        JOIN work_order wo ON wo.wo_id = w.job_id
        WHERE wo.status = 'closed' AND DATE(wo.close_date) <= ?
          AND DATE(w.event_date) <= ?
        GROUP BY w.job_id HAVING ABS(SUM(w.amount)) > 0.005
        """, (AS_OF, AS_OF)
    ).fetchall()
    check("every job closed by AS_OF has zero WIP as of AS_OF",
          not bad_closed, str(bad_closed))

    # 4 — per-job: jobs still open at AS_OF carry WIP == inflows through AS_OF
    bad_open = cur.execute(
        """
        SELECT w.job_id, ROUND(SUM(w.amount),2) bal,
               ROUND(SUM(CASE WHEN w.amount > 0 THEN w.amount ELSE 0 END),2) inflow
        FROM gl_wip_inventory w
        JOIN work_order wo ON wo.wo_id = w.job_id
        WHERE (wo.status != 'closed' OR DATE(wo.close_date) > ?)
          AND DATE(w.event_date) <= ?
        GROUP BY w.job_id
        HAVING ABS(bal - inflow) > 0.005
        """, (AS_OF, AS_OF)
    ).fetchall()
    check("every job open at AS_OF carries WIP equal to its inflows through AS_OF",
          not bad_open, str(bad_open))

    # 5 — no WIP outflow may exist for a job whose close_date is after AS_OF
    early_out = cur.execute(
        """
        SELECT COUNT(*) FROM gl_wip_inventory w
        JOIN work_order wo ON wo.wo_id = w.job_id
        WHERE w.amount < 0 AND DATE(w.event_date) <= ?
          AND (wo.status != 'closed' OR DATE(wo.close_date) > ?)
        """, (AS_OF, AS_OF)
    ).fetchone()[0]
    check("no completion outflow posted for jobs not closed by AS_OF",
          early_out == 0, str(early_out))

    conn.close()

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print(f"\nALL CHECKS PASSED — WIP {wip_bal}, RM out {rm_out}, FG {fg_bal} "
          f"as of {AS_OF}")


if __name__ == "__main__":
    main()
