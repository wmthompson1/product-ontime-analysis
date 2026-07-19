"""Seed daily synthetic work-order throughput + matching customer demand
through July 2026 — deterministic, idempotent, fail-closed.

Why (user-requested): every prior job closed by January 2026, so any mid-month
WIP snapshot after that is zero. This migration gives the plant a "live" month:
one work order completes every day of July 2026, with customer demand arriving
at the same daily cadence, so an intra-month as-of date shows real in-process
WIP (jobs opened but not yet closed) that relieves to FG day by day.

What it creates (all synthetic, SQLite-only, pure functions of the day number):
  1. CO-JUL-01 — one OPEN customer order with 31 lines, one per July day;
     line d needs part MCH-51xxx on 2026-07-<d> (desired_release = need_by −
     part lead time). Open CO ⇒ prune_erp_to_demo_scale always keeps it.
  2. WO-JUL-01..31 — one CLOSED work order per July day, each linked to its
     demand line via work_order.demand_order_line_id. WO d opens
     max(2026-07-01, close − 7d) and closes 2026-07-<d>, so all activity stays
     inside July and the June 2026 month-end reconciliation is untouched.
  3. Per WO, a self-consistent cost chain that satisfies every ledger gate:
       - one material_issue (RMT raw stock) on the open date,
       - one single-step routing (operation, status 'C', resource MC-001) whose
         actuals follow the rate model backfill_labor_chain enforces:
         hours = round(labor / run_cost_per_hr, 2),
         burden = round(hours × bur_per_hr_run, 2),
       - one aggregate labor_ticket reproducing that step's labor/burden
         (the one-posting-per-progressed-step grain the labor-chain gate uses),
       - work_order.act_mat/lab/bur = exact sums of the detail (cent-exact),
         act_ser = 0 (no outside service on these jobs).
  4. Nothing GL: run migrations/backfill_gl_ledger.py AFTER this migration —
     it replays the new material issues / labor tickets / closed WOs through
     gl_posting with idempotency keys, keeping the ledger gates green.

AS_OF shift (intentional): the data-derived anchor MAX(work_order.close_date)
moves from 2026-01-21 to 2026-07-31 — July becomes the plant's "present".
Earlier MRP backfills recompute deterministically from the live anchor on
re-run, and this migration runs AFTER them in the bootstrap chain, so a full
chain re-run always converges (this migration re-heals its own daily dates
last, exactly like expand_mrp_part_universe does for its rows).

Demo-scale bands: these are series-prefixed synthetic rows added AFTER
prune_erp_to_demo_scale in the chain (the same pattern as WO-PLN-*/CO-MRP-*).
A chain re-run may let the prune trim them, but this migration re-creates them
byte-identically afterwards, so the end state is stable. The demand lines only
reuse parts that already carry open CO-MRP demand, so the prune's demand-part
keep-set is unchanged.

Idempotency: headers use INSERT OR IGNORE on natural TEXT PKs; autoincrement
children (lines / operations / issues / tickets) are guarded by NOT EXISTS;
dates and costs are then unconditionally recomputed to the same deterministic
values, so drift self-heals. Safe to re-run with an identical result.

Run order: after every cost/schedule backfill and before backfill_gl_ledger:
    cd hf-space-inventory-sqlgen
    python migrations/seed_july_throughput.py && python migrations/backfill_gl_ledger.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_HERE)
DB_PATH = os.path.join(_APP_DIR, "app_schema", "manufacturing.db")
sys.path.insert(0, _APP_DIR)

ISO = "%Y-%m-%d"

CO_ID = "CO-JUL-01"
DAYS = 31                      # July 2026 has 31 days
YEAR, MONTH = 2026, 7
RESOURCE_ID = "MC-001"         # Haas VF-4 — canonical CNC machine
EMPLOYEE_ID = "EMP-001"
SEQ_NO = 10
CYCLE_DAYS = 7                 # nominal shop cycle; clamped to July 1
SITE = "SITE-1"

# Parts: reuse the MRP-expansion universe (already open CO-MRP demand parts,
# positive lead time + on-hand supply basis, so validate_planning_inputs and
# the prune keep-set are both unchanged). 25 MAKE parts cycled over 31 days;
# raw stock issued from the RMT raw-metal series.
MAKE_PART_COUNT = 25           # MCH-51001..MCH-51025
RAW_PART_COUNT = 15            # RMT-54001..RMT-54015


def _wo_id(d: int) -> str:
    return f"WO-JUL-{d:02d}"


def _make_part(d: int) -> str:
    return f"MCH-{51001 + (d - 1) % MAKE_PART_COUNT}"


def _raw_part(d: int) -> str:
    return f"RMT-{54001 + (d - 1) % RAW_PART_COUNT}"


def _close(d: int) -> date:
    return date(YEAR, MONTH, d)


def _open(d: int) -> date:
    return max(date(YEAR, MONTH, 1), _close(d) - timedelta(days=CYCLE_DAYS))


def _qty(d: int) -> float:
    return float(2 + d % 3)            # 2..4 units, deterministic


def _labor(d: int) -> float:
    return round(150.0 + 12.5 * d, 2)  # strictly positive, unique per day


def _raw_qty(d: int) -> float:
    return float(3 + d % 4)            # 3..6 units of raw stock


def _plan(cur) -> list[dict]:
    """Fully-resolved per-day plan; fails closed if reference data is absent."""
    row = cur.execute(
        "SELECT run_cost_per_hr, bur_per_hr_run FROM shop_resource "
        "WHERE resource_id = ?", (RESOURCE_ID,)).fetchone()
    if not row or not row[0] or not row[1]:
        raise RuntimeError(f"FAIL-CLOSED: resource {RESOURCE_ID} missing usable rates")
    run_rate, bur_rate = float(row[0]), float(row[1])

    if not cur.execute("SELECT 1 FROM EMPLOYEE WHERE employee_id = ?",
                       (EMPLOYEE_ID,)).fetchone():
        raise RuntimeError(f"FAIL-CLOSED: employee {EMPLOYEE_ID} not found")

    parts = {p: (desc, float(uc or 0.0), int(lt or 0), float(oh or 0.0))
             for p, desc, uc, lt, oh in cur.execute(
                 "SELECT part_id, part_description, unit_cost, lead_time_days, "
                 "on_hand_qty FROM part")}

    plan = []
    for d in range(1, DAYS + 1):
        mk, rw = _make_part(d), _raw_part(d)
        for pid in (mk, rw):
            if pid not in parts:
                raise RuntimeError(f"FAIL-CLOSED: part {pid} not in part master "
                                   "(run expand_mrp_part_universe first)")
        mk_desc, mk_cost, mk_lead, mk_onhand = parts[mk]
        if mk_lead <= 0 or mk_onhand <= 0:
            raise RuntimeError(
                f"FAIL-CLOSED: {mk} needs positive lead time and on-hand stock "
                "for MRP planning-input validation")
        rw_desc, rw_cost = parts[rw][0], parts[rw][1]

        lab = _labor(d)
        hours = round(lab / run_rate, 2)           # backfill_labor_chain model
        if hours <= 0:
            raise RuntimeError(f"FAIL-CLOSED: day {d} labor backs out to 0 hours")
        bur = round(hours * bur_rate, 2)
        mat = round(_raw_qty(d) * rw_cost, 2)
        if mat <= 0:
            raise RuntimeError(f"FAIL-CLOSED: day {d} material cost is not positive")

        close, open_ = _close(d), _open(d)
        # Labor is clocked the day before close, clamped to July 1 so day 1
        # never leaks labor into June (the June month-end gate must see zero
        # July-job activity).
        clock_in = max(
            datetime(close.year, close.month, close.day, 8, 0) - timedelta(days=1),
            datetime(YEAR, MONTH, 1, 8, 0),
        )
        plan.append(dict(
            day=d, wo_id=_wo_id(d), part=mk, part_desc=mk_desc, qty=_qty(d),
            raw_part=rw, raw_desc=rw_desc, raw_qty=_raw_qty(d), raw_cost=rw_cost,
            mat=mat, lab=lab, bur=bur, hours=hours,
            open=open_.strftime(ISO), close=close.strftime(ISO),
            need_by=close.strftime(ISO),
            release=(close - timedelta(days=mk_lead)).strftime(ISO),
            unit_price=round(mk_cost * 1.35, 2),
            clock_in=clock_in.strftime("%Y-%m-%d %H:%M:%S"),
            clock_out=(clock_in + timedelta(hours=max(hours, 0.25)))
            .strftime("%Y-%m-%d %H:%M:%S"),
            sched_start=f"{open_.strftime(ISO)} 08:00:00",
            sched_finish=f"{close.strftime(ISO)} 16:00:00",
        ))
    return plan


def seed(cur, plan) -> None:
    # 1. Open customer order + 31 daily demand lines.
    cur.execute(
        "INSERT OR IGNORE INTO customer_order "
        "(order_id, customer_name, order_date, site_id, status) "
        "VALUES (?, 'Aerostructures Daily Demand Program', ?, ?, 'Open')",
        (CO_ID, date(YEAR, MONTH, 1).strftime(ISO), SITE))
    for p in plan:
        cur.execute(
            "INSERT INTO customer_order_line "
            "(order_id, line_no, part_id, site_id, order_qty, unit_price, "
            " need_by_date, desired_release_date) "
            "SELECT ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS "
            "(SELECT 1 FROM customer_order_line WHERE order_id = ? AND line_no = ?)",
            (CO_ID, p["day"], p["part"], SITE, p["qty"], p["unit_price"],
             p["need_by"], p["release"], CO_ID, p["day"]))
        # self-heal: an MRP demand backfill re-run rewrites open-CO need_by
        # dates with its horizon formula; restore the daily cadence (this
        # migration runs after it in the chain, so the chain end-state wins).
        cur.execute(
            "UPDATE customer_order_line SET part_id=?, order_qty=?, "
            "unit_price=?, need_by_date=?, desired_release_date=? "
            "WHERE order_id=? AND line_no=?",
            (p["part"], p["qty"], p["unit_price"], p["need_by"], p["release"],
             CO_ID, p["day"]))

    line_ids = dict(cur.execute(
        "SELECT line_no, order_line_id FROM customer_order_line "
        "WHERE order_id = ?", (CO_ID,)))

    # 2. One closed work order per day + its cost chain.
    for p in plan:
        wo = p["wo_id"]
        cur.execute(
            "INSERT OR IGNORE INTO work_order "
            "(wo_id, workorder_type, part_id, part_description, quantity, "
            " status, open_date, close_date, required_date, routing_template, "
            " site_id) "
            "VALUES (?, 'W', ?, ?, ?, 'closed', ?, ?, ?, 'MACHINED', ?)",
            (wo, p["part"], p["part_desc"], p["qty"],
             p["open"], p["close"], p["close"], SITE))
        cur.execute(
            "UPDATE work_order SET part_id=?, part_description=?, quantity=?, "
            "status='closed', open_date=?, close_date=?, required_date=?, "
            "act_mat_cost=?, act_lab_cost=?, act_bur_cost=?, act_ser_cost=0.0, "
            "sched_start_date=?, sched_finish_date=?, desired_rls_date=?, "
            "demand_order_line_id=? WHERE wo_id=?",
            (p["part"], p["part_desc"], p["qty"], p["open"], p["close"],
             p["close"], p["mat"], p["lab"], p["bur"],
             p["sched_start"], p["sched_finish"], p["open"],
             line_ids[p["day"]], wo))

        cur.execute(
            "INSERT INTO operation "
            "(wo_id, workorder_type, sequence_no, resource_id, run_type, "
            " act_run_hrs, est_atl_lab_cost, est_atl_bur_cost, "
            " act_atl_lab_cost, act_atl_bur_cost, status, "
            " sched_start_date, sched_finish_date, close_date) "
            "SELECT ?, 'W', ?, ?, 'HR', ?, ?, ?, ?, ?, 'C', ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM operation WHERE wo_id = ?)",
            (wo, SEQ_NO, RESOURCE_ID, p["hours"], p["lab"], p["bur"],
             p["lab"], p["bur"], p["sched_start"], p["sched_finish"],
             p["close"], wo))
        cur.execute(
            "UPDATE operation SET act_run_hrs=?, est_atl_lab_cost=?, "
            "est_atl_bur_cost=?, act_atl_lab_cost=?, act_atl_bur_cost=?, "
            "status='C', close_date=? WHERE wo_id=? AND sequence_no=?",
            (p["hours"], p["lab"], p["bur"], p["lab"], p["bur"],
             p["close"], wo, SEQ_NO))

        cur.execute(
            "INSERT INTO material_issue "
            "(wo_id, part_id, part_description, quantity, unit_cost, "
            " total_cost, issue_date, issued_by) "
            "SELECT ?, ?, ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM material_issue WHERE wo_id = ?)",
            (wo, p["raw_part"], p["raw_desc"], p["raw_qty"], p["raw_cost"],
             p["mat"], p["open"], EMPLOYEE_ID, wo))
        cur.execute(
            "UPDATE material_issue SET part_id=?, part_description=?, "
            "quantity=?, unit_cost=?, total_cost=?, issue_date=?, issued_by=? "
            "WHERE wo_id=?",
            (p["raw_part"], p["raw_desc"], p["raw_qty"], p["raw_cost"],
             p["mat"], p["open"], EMPLOYEE_ID, wo))

        cur.execute(
            "INSERT INTO labor_ticket "
            "(wo_id, sequence_no, employee_id, resource_id, clock_in, "
            " clock_out, total_hours, labor_cost, burden_cost) "
            "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM labor_ticket WHERE wo_id = ?)",
            (wo, SEQ_NO, EMPLOYEE_ID, RESOURCE_ID, p["clock_in"],
             p["clock_out"], p["hours"], p["lab"], p["bur"], wo))
        cur.execute(
            "UPDATE labor_ticket SET clock_in=?, clock_out=?, total_hours=?, "
            "labor_cost=?, burden_cost=? WHERE wo_id=? AND sequence_no=?",
            (p["clock_in"], p["clock_out"], p["hours"], p["lab"], p["bur"],
             wo, SEQ_NO))


def validate(cur, plan) -> None:
    """Fail closed on any drift between the seeded layers (pre-commit)."""
    failures = []

    n = cur.execute("SELECT COUNT(*) FROM work_order "
                    "WHERE wo_id LIKE 'WO-JUL-%' AND status='closed'").fetchone()[0]
    if n != DAYS:
        failures.append(f"expected {DAYS} closed WO-JUL work orders, found {n}")

    n = cur.execute("SELECT COUNT(*) FROM customer_order_line "
                    "WHERE order_id = ?", (CO_ID,)).fetchone()[0]
    if n != DAYS:
        failures.append(f"expected {DAYS} {CO_ID} demand lines, found {n}")

    # one close per July day, evenly: exactly one WO closes on each date
    rows = cur.execute(
        "SELECT close_date, COUNT(*) FROM work_order WHERE wo_id LIKE 'WO-JUL-%' "
        "GROUP BY close_date HAVING COUNT(*) != 1").fetchall()
    if rows:
        failures.append(f"uneven daily throughput: {rows[:3]}")

    # all activity strictly inside July 2026 (June month-end must be untouched)
    n = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE wo_id LIKE 'WO-JUL-%' AND ("
        "date(open_date) < '2026-07-01' OR date(close_date) > '2026-07-31')"
    ).fetchone()[0]
    if n:
        failures.append(f"{n} WO-JUL work orders leak outside July 2026")
    n = cur.execute(
        "SELECT COUNT(*) FROM labor_ticket t JOIN work_order w ON w.wo_id=t.wo_id "
        "WHERE w.wo_id LIKE 'WO-JUL-%' AND ("
        "date(t.clock_in) < '2026-07-01' OR date(t.clock_out) > '2026-07-31')"
    ).fetchone()[0]
    if n:
        failures.append(f"{n} WO-JUL labor tickets leak outside July 2026")
    n = cur.execute(
        "SELECT COUNT(*) FROM material_issue m JOIN work_order w ON w.wo_id=m.wo_id "
        "WHERE w.wo_id LIKE 'WO-JUL-%' AND ("
        "date(m.issue_date) < '2026-07-01' OR date(m.issue_date) > '2026-07-31')"
    ).fetchone()[0]
    if n:
        failures.append(f"{n} WO-JUL material issues leak outside July 2026")

    # cent-exact chain ties: detail sums == operation actuals == WO rollup
    for wo_id, mat, lab, bur, s_mat, s_lab, s_bur, o_lab, o_bur, dol in cur.execute(
        "SELECT w.wo_id, w.act_mat_cost, w.act_lab_cost, w.act_bur_cost, "
        " (SELECT COALESCE(SUM(total_cost),0) FROM material_issue m WHERE m.wo_id=w.wo_id), "
        " (SELECT COALESCE(SUM(labor_cost),0) FROM labor_ticket t WHERE t.wo_id=w.wo_id), "
        " (SELECT COALESCE(SUM(burden_cost),0) FROM labor_ticket t WHERE t.wo_id=w.wo_id), "
        " (SELECT COALESCE(SUM(act_atl_lab_cost),0) FROM operation o WHERE o.wo_id=w.wo_id), "
        " (SELECT COALESCE(SUM(act_atl_bur_cost),0) FROM operation o WHERE o.wo_id=w.wo_id), "
        " w.demand_order_line_id "
        "FROM work_order w WHERE w.wo_id LIKE 'WO-JUL-%'"
    ).fetchall():
        for name, a, b in (("material", mat, s_mat), ("labor", lab, s_lab),
                           ("burden", bur, s_bur), ("op-labor", lab, o_lab),
                           ("op-burden", bur, o_bur)):
            if round(a - b, 2) != 0.0:
                failures.append(f"{wo_id}: {name} drift {a} vs {b}")
        if not dol:
            failures.append(f"{wo_id}: demand_order_line_id not linked")

    if failures:
        raise RuntimeError("July throughput validation FAILED:\n  "
                           + "\n  ".join(failures))


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        plan = _plan(cur)
        seed(cur, plan)
        validate(cur, plan)
        con.commit()
    except Exception:
        con.rollback()
        raise
    # post-commit: MRP planning inputs must still validate with the new anchor
    from mrp_engine import validate_planning_inputs, compute_as_of
    summary = validate_planning_inputs(con)
    as_of = compute_as_of(con)
    con.close()
    print(f"Seeded {DAYS} daily July work orders + {DAYS} demand lines "
          f"(AS_OF now {as_of}); MRP inputs valid: "
          f"{summary['demand_parts']} demand parts in horizon")
    return 0


if __name__ == "__main__":
    sys.exit(main())
