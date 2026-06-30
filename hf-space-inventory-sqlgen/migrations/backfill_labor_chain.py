"""
Migration: Rebuild the internal labor chain BOTTOM-UP so all three layers
agree — labor_ticket -> operation actuals -> work_order rollup — with a
rate-consistent burden.

Why
---
Before this migration the three layers disagreed:

  * work_order.act_lab_cost / act_bur_cost were the source-of-truth rollups
    (built from recognized estimates, then reconciled DOWN to the operation
    actuals by backfill_operation_actuals.py), and
  * labor_ticket rows were decorative: their dollars were seeded as
    hours*rate WITHOUT the build quantity, so they summed to only a small
    fraction of the operation actuals and covered only ~half the steps.

So a job's labor could not be read from the floor detail up: the time tickets
did not sum to the operation, and (because labor and burden had been
distributed INDEPENDENTLY) a single ticket's hours could not reproduce both
its labor and its burden through one (hours x rate) posting.

What this migration does
------------------------
It rebuilds the ticket layer as the grounding detail and re-derives burden so
the rate model (labor = hours x run_cost_per_hr, burden = hours x bur_per_hr_run)
holds end-to-end, while keeping the reconciled LABOR headline unchanged:

  1. LABOR is the anchor. Each progressed in-house step
     (service_id IS NULL AND act_atl_lab_cost > 0) already carries a labor
     actual that ties to the work-order rollup. We treat that labor as truth
     and back out the hours that produced it at the step's resource run rate:
         hours = act_atl_lab_cost / shop_resource.run_cost_per_hr
     A single labor posting (one aggregate labor_ticket per step) is minted
     with labor_cost = the step's labor actual, so SUM(ticket labor) per step
     reproduces the operation labor to the cent, and the work-order labor
     rollup is unchanged.

  2. BURDEN becomes rate-consistent. Instead of an independently distributed
     burden, each step's burden is re-derived from the SAME hours at the
     resource burden rate:
         burden = hours x shop_resource.bur_per_hr_run
     The ticket carries that burden, the operation's act_atl_bur_cost is set
     to it, and the work_order.act_bur_cost rollup is recomputed as the sum of
     its operations. Total burden therefore drifts to whatever the hours x
     burden-rate model yields (a clean, defensible standard-cost burden), and
     burden ties out bottom-up: ticket -> operation -> work order.

  3. Queued in-house steps (act_atl_lab_cost = 0) accrue no ticket and 0
     internal burden. Outside-service steps (service_id IS NOT NULL) are never
     given labor tickets and their act_atl_ser_cost is left untouched (it is
     owned by backfill_operation_actuals.py from received service POs).

The certified ArangoDB graph and graph_metadata.json are NEVER touched: this
changes only cell values in tables that are already graph nodes, not the graph
structure.

Idempotency
-----------
Every value is a pure function of existing rows (operation labor actuals,
resource rates, operation schedule). The ticket layer is fully rebuilt each run
(DELETE then re-INSERT with deterministic ticket_ids ordered by
(wo_id, sequence_no)); clock and created_at timestamps are derived from the
operation schedule, never wall-clock. Re-running reproduces the identical state.

Run order
---------
AFTER backfill_operation_actuals.py (the reconciled operation labor actuals it
anchors on must already be set), which itself runs after
backfill_supplier_rating_and_wo_actuals.py and backfill_operation_progress.py.
Safe to re-run.

    cd hf-space-inventory-sqlgen
    python migrations/backfill_labor_chain.py
"""

import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# Labor is posted starting at the shift open on the step's scheduled start day.
SHIFT_START_HOUR = 8
# Deterministic fallback clock anchor for the (live: zero) steps with no schedule.
EPOCH = "2000-01-01"


def _parse_dt(value):
    """Parse a stored date/datetime string into a datetime, or None."""
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Resource rates: resource_id -> (run_cost_per_hr, bur_per_hr_run).
    rates = {
        r[0]: (r[1] or 0.0, r[2] or 0.0)
        for r in cur.execute(
            "SELECT resource_id, run_cost_per_hr, bur_per_hr_run FROM shop_resource"
        )
    }
    # One stable operator per work center (deterministic employee id).
    emp_of = {rid: f"EMP-{i + 1:03d}" for i, rid in enumerate(sorted(rates))}

    # Labor is the anchor: capture the headline now so we can prove the rebuild
    # leaves it unchanged (a WO with labor but NO operations would otherwise be
    # silently zeroed by the rollup below — we fail closed on that instead).
    labor_before = round(
        cur.execute("SELECT COALESCE(SUM(act_lab_cost), 0.0) FROM work_order")
        .fetchone()[0],
        2,
    )

    # Progressed in-house labor steps — one aggregate labor posting per step.
    ops = cur.execute(
        "SELECT wo_id, sequence_no, resource_id, act_atl_lab_cost, sched_start_date "
        "FROM operation "
        "WHERE service_id IS NULL AND act_atl_lab_cost > 0 "
        "ORDER BY wo_id, sequence_no"
    ).fetchall()

    tickets = []           # explicit-id rows for executemany
    op_burden = {}         # (wo_id, sequence_no) -> burden_cost
    no_rate = []           # progressed in-house steps with no usable run rate
    zero_hours = []        # steps whose labor>0 but back out to 0.00 hours
    tid = 0
    for wo_id, seq, rid, lab, sched in ops:
        run_rate, bur_rate = rates.get(rid, (0.0, 0.0))
        lab = round(lab or 0.0, 2)
        if run_rate <= 0:
            # Cannot back out hours without a run rate. Inventing hours would
            # break the rate model AND drop this step's labor from the ticket
            # rollup (silent drift). Record it and fail closed below.
            no_rate.append((wo_id, seq))
            continue
        hours = round(lab / run_rate, 2)
        if hours <= 0:
            # Positive labor that rounds to zero hours would mint a zero-duration
            # ticket and zero burden — the rate model no longer holds. Fail closed.
            zero_hours.append((wo_id, seq))
            continue
        burden = round(hours * bur_rate, 2)

        anchor = _parse_dt(sched) or _parse_dt(EPOCH)
        clock_in_dt = anchor.replace(
            hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0
        )
        clock_out_dt = clock_in_dt + timedelta(hours=hours)
        clock_in = clock_in_dt.strftime("%Y-%m-%d %H:%M:%S")
        clock_out = clock_out_dt.strftime("%Y-%m-%d %H:%M:%S")

        tid += 1
        tickets.append(
            (tid, wo_id, seq, emp_of.get(rid, "EMP-000"), rid,
             clock_in, clock_out, hours, lab, burden, clock_out)
        )
        op_burden[(wo_id, seq)] = burden

    # Rebuild the ticket layer from scratch (deterministic ids -> idempotent).
    cur.execute("DELETE FROM labor_ticket")
    cur.execute("DELETE FROM sqlite_sequence WHERE name = 'labor_ticket'")
    cur.executemany(
        "INSERT INTO labor_ticket (ticket_id, wo_id, sequence_no, employee_id, "
        "resource_id, clock_in, clock_out, total_hours, labor_cost, burden_cost, "
        "created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        tickets,
    )

    # Operation burden = its rate-consistent ticket burden. In-house steps with
    # no ticket (queued) -> 0. Outside-service steps keep their own actuals.
    op_updates = [
        (op_burden.get((wo_id, seq), 0.0), rowid_pk)
        for rowid_pk, wo_id, seq, service_id in cur.execute(
            "SELECT rowid_pk, wo_id, sequence_no, service_id FROM operation"
        ).fetchall()
        if service_id is None
    ]
    cur.executemany(
        "UPDATE operation SET act_atl_bur_cost = ? WHERE rowid_pk = ?", op_updates
    )

    # Work-order rollups = SUM of operation actuals. Labor is unchanged (it was
    # the anchor); burden is the new rate-consistent total.
    cur.execute(
        """
        UPDATE work_order SET
          act_lab_cost = COALESCE(
            (SELECT SUM(o.act_atl_lab_cost) FROM operation o
             WHERE o.wo_id = work_order.wo_id), 0.0),
          act_bur_cost = COALESCE(
            (SELECT SUM(o.act_atl_bur_cost) FROM operation o
             WHERE o.wo_id = work_order.wo_id), 0.0)
        """
    )
    # ── verification (against the UNCOMMITTED rebuild) ────────────────────────
    # The cursor sees the pending changes; we prove every layer ties out BEFORE
    # committing and fail closed (rollback) on any drift, so a bad run never
    # leaves a half-reconciled database behind.

    # ticket -> operation reconciliation (labor and burden, per wo_id+sequence_no)
    t2o = cur.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT o.rowid_pk,
                 ROUND(o.act_atl_lab_cost,2) AS ol, ROUND(COALESCE(t.tl,0),2) AS tl,
                 ROUND(o.act_atl_bur_cost,2) AS ob, ROUND(COALESCE(t.tb,0),2) AS tb
          FROM operation o
          LEFT JOIN (
            SELECT wo_id, sequence_no, SUM(labor_cost) tl, SUM(burden_cost) tb
            FROM labor_ticket GROUP BY wo_id, sequence_no
          ) t ON t.wo_id = o.wo_id AND t.sequence_no = o.sequence_no
          WHERE o.service_id IS NULL
        ) x
        WHERE ABS(ol - tl) >= 0.01 OR ABS(ob - tb) >= 0.01
        """
    ).fetchone()[0]

    # operation -> work-order reconciliation (labor and burden)
    o2w = cur.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT w.wo_id,
                 ROUND(w.act_lab_cost,2) AS wl, ROUND(COALESCE(o.ol,0),2) AS ol,
                 ROUND(w.act_bur_cost,2) AS wb, ROUND(COALESCE(o.ob,0),2) AS ob
          FROM work_order w
          LEFT JOIN (
            SELECT wo_id, SUM(act_atl_lab_cost) ol, SUM(act_atl_bur_cost) ob
            FROM operation GROUP BY wo_id
          ) o ON o.wo_id = w.wo_id
        ) t
        WHERE ABS(wl - ol) >= 0.01 OR ABS(wb - ob) >= 0.01
        """
    ).fetchone()[0]

    # Labor is the anchor — the rebuild must not move the headline by a cent.
    labor_after = round(
        cur.execute("SELECT COALESCE(SUM(act_lab_cost), 0.0) FROM work_order")
        .fetchone()[0],
        2,
    )

    problems = []
    if no_rate:
        problems.append(
            f"{len(no_rate)} progressed in-house step(s) have no usable run rate "
            f"(run_cost_per_hr <= 0); cannot back out hours, e.g. {no_rate[:5]}"
        )
    if zero_hours:
        problems.append(
            f"{len(zero_hours)} step(s) carry labor that rounds to 0.00 hours; "
            f"the rate model would break, e.g. {zero_hours[:5]}"
        )
    if t2o:
        problems.append(f"{t2o} in-house step(s) whose tickets do NOT tie to the operation")
    if o2w:
        problems.append(f"{o2w} work order(s) whose operation actuals do NOT tie to the rollup")
    if abs(labor_after - labor_before) >= 0.01:
        problems.append(
            f"labor headline changed: before={labor_before} after={labor_after} "
            "(a WO with labor but no operations was zeroed by the rollup)"
        )

    if problems:
        conn.rollback()
        conn.close()
        raise RuntimeError(
            "backfill_labor_chain aborted — the labor chain does not reconcile:\n  - "
            + "\n  - ".join(problems)
        )

    conn.commit()

    # ── reporting ────────────────────────────────────────────────────────────
    print(f"  labor tickets rebuilt: {len(tickets)}")
    tot = cur.execute(
        "SELECT ROUND(SUM(labor_cost),2), ROUND(SUM(burden_cost),2) FROM labor_ticket"
    ).fetchone()
    print(f"  ticket totals  labor={tot[0]}  burden={tot[1]}")
    wo = cur.execute(
        "SELECT ROUND(SUM(act_lab_cost),2), ROUND(SUM(act_bur_cost),2) FROM work_order"
    ).fetchone()
    print(f"  work-order rollup  labor={wo[0]}  burden={wo[1]}")
    print(f"  in-house steps whose tickets do NOT tie to the operation: {t2o}")
    print(f"  work orders whose operation actuals do NOT tie to the rollup: {o2w}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
