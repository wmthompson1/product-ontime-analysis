"""
Migration: deterministic GL ledger backfill — replay existing operational
documents through the simple posting functions (gl_posting.py) so the
gl_* tables tell the real job-costing story.

What gets replayed (in deterministic source-document order):
  1. material_issue rows      -> post_material_issue  (RM -> WIP, MATERIAL)
     amount = total_cost, event_date = issue_date,
     idempotency key = (material_issue, issue_id, RM_ISSUE)
  2. labor_ticket rows        -> post_labor            (WIP, LABOR)
     amount = labor_cost, event_date = clock_out,
     key = (labor_ticket, ticket_id, LABOR)
  3. labor_ticket rows        -> post_overhead         (WIP, BURDEN)
     amount = burden_cost, event_date = clock_out,
     key = (labor_ticket, ticket_id, BURDEN)
  4. closed work orders       -> post_job_completion   (WIP -> FG)
     amount = act_mat_cost + act_lab_cost + act_bur_cost (the cost sourced
     from these documents; outside-service cost is out of scope),
     event_date = close_date, key = (work_order, wo_id, FG_COMPLETION).

Rules:
  * Planned orders (WO-PLN-*) and non-closed work orders are NEVER completed.
  * Zero-amount source lines are skipped (they would post nothing).
  * Idempotent: the posting functions no-op on an existing
    (source_table, source_id, event_type) — re-runs create no duplicates.
  * Fail-closed tie-out BEFORE commit: per-job gl_job_cost_detail sums for
    MATERIAL / LABOR / BURDEN must equal work_order.act_mat_cost /
    act_lab_cost / act_bur_cost to the cent; drift aborts with named
    offenders and rolls back.
  * All event dates are data-derived from the source documents, never
    wall-clock. A source row missing its date fails closed.

Run order: AFTER add_gl_ledger_tables.py (tables) and AFTER every migration
that shapes material_issue / labor_ticket / work_order actuals
(backfill_labor_chain.py et al.). Safe to re-run.

    cd hf-space-inventory-sqlgen
    python migrations/backfill_gl_ledger.py [--db PATH]
"""

import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

from gl_posting import (  # noqa: E402
    post_material_issue,
    post_labor,
    post_overhead,
    post_job_completion,
)

DEFAULT_DB = os.path.join(HF_DIR, "app_schema", "manufacturing.db")


def run(db_path: str = DEFAULT_DB) -> None:
    if not os.path.exists(db_path):
        raise SystemExit(f"FAIL-CLOSED: database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    missing_dates = []
    counts = {"material": 0, "labor": 0, "burden": 0, "completion": 0}

    # 1. Material issues: RM -> WIP.
    for issue_id, wo_id, part_id, total_cost, issue_date in cur.execute(
        "SELECT issue_id, wo_id, part_id, total_cost, issue_date "
        "FROM material_issue ORDER BY issue_id"
    ).fetchall():
        amt = round(total_cost or 0.0, 2)
        if amt <= 0:
            continue
        if not issue_date:
            missing_dates.append(("material_issue", issue_id))
            continue
        if post_material_issue(cur, wo_id, part_id, amt, issue_date,
                               "material_issue", issue_id) is not None:
            counts["material"] += 1

    # Part of each work order (for WIP inventory line part linkage).
    wo_part = dict(cur.execute("SELECT wo_id, part_id FROM work_order"))

    # 2 + 3. Labor tickets: labor and burden into WIP.
    for ticket_id, wo_id, labor_cost, burden_cost, clock_out in cur.execute(
        "SELECT ticket_id, wo_id, labor_cost, burden_cost, clock_out "
        "FROM labor_ticket ORDER BY ticket_id"
    ).fetchall():
        if not clock_out:
            missing_dates.append(("labor_ticket", ticket_id))
            continue
        part_id = wo_part.get(wo_id)
        lab = round(labor_cost or 0.0, 2)
        bur = round(burden_cost or 0.0, 2)
        if lab > 0 and post_labor(cur, wo_id, part_id, lab, clock_out,
                                  "labor_ticket", ticket_id) is not None:
            counts["labor"] += 1
        if bur > 0 and post_overhead(cur, wo_id, part_id, bur, clock_out,
                                     "labor_ticket", ticket_id) is not None:
            counts["burden"] += 1

    # 4. Job completions: WIP -> FG at the WO close_date. Planned orders
    #    (WO-PLN-*) and non-closed WOs are never completed.
    for wo_id, part_id, close_date, mat, lab, bur in cur.execute(
        "SELECT wo_id, part_id, close_date, act_mat_cost, act_lab_cost, "
        "act_bur_cost FROM work_order "
        "WHERE status = 'closed' AND wo_id NOT LIKE 'WO-PLN-%' "
        "ORDER BY wo_id"
    ).fetchall():
        amt = round((mat or 0.0) + (lab or 0.0) + (bur or 0.0), 2)
        if amt <= 0:
            continue
        if not close_date:
            missing_dates.append(("work_order", wo_id))
            continue
        if post_job_completion(cur, wo_id, part_id, amt, close_date,
                               "work_order", wo_id) is not None:
            counts["completion"] += 1

    # ── fail-closed verification (against the UNCOMMITTED postings) ─────────
    problems = []
    if missing_dates:
        problems.append(
            f"{len(missing_dates)} source row(s) missing a data-derived date, "
            f"e.g. {missing_dates[:5]}"
        )

    # Per-job cost-detail tie-out to work_order actuals (costs sourced from
    # these documents: material, labor, burden — service is out of scope).
    for element, wo_col in (("MATERIAL", "act_mat_cost"),
                            ("LABOR", "act_lab_cost"),
                            ("BURDEN", "act_bur_cost")):
        offenders = cur.execute(
            f"""
            SELECT w.wo_id, ROUND(w.{wo_col},2), ROUND(COALESCE(d.s,0),2)
            FROM work_order w
            LEFT JOIN (
              SELECT job_id, SUM(amount) s FROM gl_job_cost_detail
              WHERE event_type = ? GROUP BY job_id
            ) d ON d.job_id = w.wo_id
            WHERE ABS(ROUND(w.{wo_col},2) - ROUND(COALESCE(d.s,0),2)) >= 0.01
            ORDER BY w.wo_id
            """,
            (element,),
        ).fetchall()
        if offenders:
            problems.append(
                f"{len(offenders)} work order(s) whose {element} ledger detail "
                f"does not tie to work_order.{wo_col}, e.g. {offenders[:5]}"
            )

    # Structural sanity: completions only on closed non-planned WOs.
    bad_completion = cur.execute(
        "SELECT COUNT(*) FROM gl_events e JOIN work_order w ON w.wo_id = e.job_id "
        "WHERE e.event_type = 'FG_COMPLETION' "
        "AND (w.status != 'closed' OR w.wo_id LIKE 'WO-PLN-%')"
    ).fetchone()[0]
    if bad_completion:
        problems.append(
            f"{bad_completion} FG_COMPLETION event(s) on planned or non-closed WOs"
        )

    if problems:
        conn.rollback()
        conn.close()
        raise SystemExit(
            "backfill_gl_ledger aborted — the ledger does not tie out:\n  - "
            + "\n  - ".join(problems)
        )

    conn.commit()

    # ── reporting ────────────────────────────────────────────────────────────
    print(f"  postings this run: material={counts['material']} "
          f"labor={counts['labor']} burden={counts['burden']} "
          f"completions={counts['completion']}")
    for t in ("gl_events", "gl_raw_materials_inventory", "gl_wip_inventory",
              "gl_finished_goods_inventory", "gl_job_cost_detail"):
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")
    wip = cur.execute(
        "SELECT ROUND(SUM(amount),2) FROM gl_wip_inventory"
    ).fetchone()[0]
    fg = cur.execute(
        "SELECT ROUND(SUM(amount),2) FROM gl_finished_goods_inventory"
    ).fetchone()[0]
    print(f"  WIP balance={wip}  FG balance={fg}")
    conn.close()
    print("Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()
    run(args.db)
