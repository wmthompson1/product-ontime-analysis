"""
Migration: MRP demand-supply data foundation (Cycle 1, horizon-aware).

Why this is needed (the seeders never gave demand a due date nor placed open
supply into a forward planning horizon, so a time-phased MRP grid had nothing to
bucket):
  - customer_order_line had no need-by / release date, so open demand could not
    be placed into monthly buckets.
  - work_order carried no outside-service service_date / vendor at the header, so
    outside-service supply could not be shown.
  - every open purchase order and non-closed work order was due in the PAST
    (required_date <= ~mid-2026, before the data-derived as-of), so the forward
    horizon had zero scheduled receipts.

What this migration establishes (all synthetic, SQLite-only, deterministic):
  1. customer_order_line.need_by_date + .desired_release_date
       need_by_date        = a deterministic month/day inside the horizon,
                             seeded by crc32(order_line_id, as_of).
       desired_release_date = need_by_date - part.lead_time_days (may fall before
                             the horizon -> "Past Due" release; left NULL only
                             when the part has no lead time, which the fail-closed
                             validation then flags).
  2. work_order.service_date + .vendor_id  (outside_service work orders only;
     DISPLAY-ONLY enrichment — netting keys WO supply off required_date, not this)
       vendor_id    = the WO's own outside-operation vendor when present, else a
                      deterministic outside-service supplier.
       service_date = the outside operation's scheduled finish, else the WO
                      required_date, else a deterministic in-window date.
  3. Supply placed into the horizon so scheduled receipts are realistic:
       - Open purchase orders and non-closed work orders whose required_date is
         before PLAN_START are rescheduled forward to a deterministic in-horizon
         due date. Only past-due OPEN POs (which have zero receiving rows) and
         non-closed WOs (which have no close_date) are touched, so supplier
         scorecards and on-time-delivery metrics are never affected.
       - A fallback open PO ("PO-MRP-<part_id>", INSERT OR IGNORE) is created for
         any BUY part that has open horizon demand but no open PO receipt in the
         horizon, so every purchased demand part has a scheduled receipt.

Anchor (data-derived, never wall-clock):
  as_of      = MAX(work_order.close_date) or FALLBACK_AS_OF (mrp_engine).
  PLAN_START = first day of the as-of month. Reschedule targets are always in
               [PLAN_START, PLAN_START+6mo), so "required_date < PLAN_START" is a
               true fixed-point guard: a second run reschedules nothing.

Idempotency: need_by_date / desired_release_date / service_date / vendor_id are
pure functions of stable keys (recomputed to the same value every run); supply
reschedules are guarded by "< PLAN_START"; fallback POs use INSERT OR IGNORE.
Safe to re-run with an identical result. The certified ArangoDB graph is never
touched. The migration ends by running the fail-closed planning-input validation.

Run order: AFTER the ERP seeders + add_wave4_traceability_tables.py (needs
customer_order_line) and backfill_operation_schedule.py (uses the WO schedule for
service_date). Safe to re-run.
    cd hf-space-inventory-sqlgen
    python migrations/backfill_mrp_demand_supply.py
"""

import os
import sqlite3
import sys
import zlib
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mrp_engine as eng  # noqa: E402  (path set above)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")
ISO = eng.ISO


def _crc(*parts) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def _widen(cur, table, columns):
    """Add columns that don't exist yet (PRAGMA-guarded; ALTER errors on dup)."""
    existing = {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    added = []
    for column, decl in columns.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {decl}")
            added.append(column)
    return added


def _horizon_date(seed_key: str, plan_start: date, as_of: date) -> date:
    """A deterministic date inside [PLAN_START, PLAN_START + HORIZON_MONTHS).

    bucket in 0..HORIZON_MONTHS-1, day in 1..28 (safe for every month). Always
    on/after PLAN_START, so it survives the "< PLAN_START" reschedule guard.
    """
    bucket = _crc(seed_key, as_of, "B") % eng.HORIZON_MONTHS
    day = _crc(seed_key, as_of, "D") % 28 + 1
    base = eng.add_months(plan_start, bucket)
    return date(base.year, base.month, day)


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    as_of = eng.compute_as_of(conn)
    plan_start = eng.plan_start(as_of)
    horizon_start, horizon_end = eng.horizon_bounds(eng.month_buckets(as_of))

    # 1. Schema: add the demand-timing + outside-service columns in place. -----
    added_col = _widen(
        cur,
        "customer_order_line",
        {
            "need_by_date": "need_by_date DATE",
            "desired_release_date": "desired_release_date DATE",
        },
    )
    added_col += _widen(
        cur,
        "work_order",
        {
            "service_date": "service_date DATE",
            "vendor_id": "vendor_id TEXT",
        },
    )

    # part lead times (for desired_release_date offset).
    lead = {
        r[0]: r[1] for r in cur.execute("SELECT part_id, lead_time_days FROM part")
    }

    # 2. Demand timing: need_by_date + desired_release_date on OPEN CO lines. ---
    demand_updates = []
    for order_line_id, part_id in cur.execute(
        """
        SELECT l.order_line_id, l.part_id
        FROM customer_order_line l
        JOIN customer_order o ON o.order_id = l.order_id
        WHERE o.status = ?
        """,
        (eng.OPEN_CO_STATUS,),
    ).fetchall():
        need_by = _horizon_date(f"col:{order_line_id}", plan_start, as_of)
        lt = lead.get(part_id)
        rel = need_by - timedelta(days=int(lt)) if lt else None
        demand_updates.append(
            (need_by.strftime(ISO), rel.strftime(ISO) if rel else None, order_line_id)
        )
    cur.executemany(
        "UPDATE customer_order_line SET need_by_date=?, desired_release_date=? "
        "WHERE order_line_id=?",
        demand_updates,
    )

    # 3. Outside-service enrichment: service_date + vendor_id (display-only). ---
    fallback_vendor = cur.execute(
        "SELECT supplier_id FROM suppliers WHERE outside_service=1 AND active=1 "
        "ORDER BY supplier_id LIMIT 1"
    ).fetchone()
    fallback_vendor = fallback_vendor[0] if fallback_vendor else None

    os_updates = []
    for wo_id, required_date in cur.execute(
        "SELECT wo_id, required_date FROM work_order WHERE outside_service=1"
    ).fetchall():
        # Vendor: the WO's own outside-operation vendor, else a stable fallback.
        op_vendor = cur.execute(
            "SELECT vendor_id FROM operation "
            "WHERE wo_id=? AND vendor_id IS NOT NULL "
            "ORDER BY sequence_no LIMIT 1",
            (wo_id,),
        ).fetchone()
        vendor_id = (op_vendor[0] if op_vendor else None) or fallback_vendor
        # Service date: outside op scheduled finish, else WO required_date, else
        # a deterministic in-window date.
        op_finish = cur.execute(
            "SELECT MAX(sched_finish_date) FROM operation "
            "WHERE wo_id=? AND vendor_id IS NOT NULL",
            (wo_id,),
        ).fetchone()
        service_date = (
            eng._parse(op_finish[0] if op_finish else None)
            or eng._parse(required_date)
            or _horizon_date(f"wosvc:{wo_id}", plan_start, as_of)
        )
        os_updates.append((service_date.strftime(ISO), vendor_id, wo_id))
    cur.executemany(
        "UPDATE work_order SET service_date=?, vendor_id=? WHERE wo_id=?",
        os_updates,
    )

    # 4. Place supply into the horizon (past-due -> deterministic in-horizon). --
    plan_start_iso = plan_start.strftime(ISO)

    po_rows = cur.execute(
        "SELECT po_id, required_date FROM purchase_order "
        "WHERE status='Open' AND (required_date IS NULL OR date(required_date) < ?)",
        (plan_start_iso,),
    ).fetchall()
    po_reschedules = [
        (_horizon_date(f"po:{po_id}", plan_start, as_of).strftime(ISO), po_id)
        for po_id, _rd in po_rows
    ]
    cur.executemany(
        "UPDATE purchase_order SET required_date=? WHERE po_id=?", po_reschedules
    )

    wo_rows = cur.execute(
        f"SELECT wo_id, required_date FROM work_order "
        f"WHERE status IN ({eng._in_clause(eng.NONCLOSED_WO_STATUSES)}) "
        f"AND (required_date IS NULL OR date(required_date) < ?)",
        (*eng.NONCLOSED_WO_STATUSES, plan_start_iso),
    ).fetchall()
    wo_reschedules = [
        (_horizon_date(f"wo:{wo_id}", plan_start, as_of).strftime(ISO), wo_id)
        for wo_id, _rd in wo_rows
    ]
    cur.executemany(
        "UPDATE work_order SET required_date=? WHERE wo_id=?", wo_reschedules
    )

    # 5. Fallback open PO for BUY demand parts with no in-horizon PO receipt. ---
    buckets = eng.month_buckets(as_of)
    fallback_material_supplier = cur.execute(
        "SELECT supplier_id FROM suppliers WHERE outside_service=0 AND active=1 "
        "ORDER BY supplier_id LIMIT 1"
    ).fetchone()
    fallback_material_supplier = (
        fallback_material_supplier[0] if fallback_material_supplier else None
    )

    buy_demand = cur.execute(
        """
        SELECT l.part_id, MIN(p.part_description), SUM(l.order_qty)
        FROM customer_order_line l
        JOIN customer_order o ON o.order_id = l.order_id
        JOIN part p           ON p.part_id  = l.part_id
        WHERE o.status = ?
          AND p.part_class = 'BUY'
          AND l.need_by_date IS NOT NULL
          AND date(l.need_by_date) >= ? AND date(l.need_by_date) < ?
        GROUP BY l.part_id
        """,
        (eng.OPEN_CO_STATUS, horizon_start.isoformat(), horizon_end.isoformat()),
    ).fetchall()

    fallback_pos = 0
    for part_id, part_desc, demand_qty in buy_demand:
        if eng.has_scheduled_receipt_in_horizon(conn, part_id, buckets):
            continue
        if not fallback_material_supplier:
            break
        po_id = f"PO-MRP-{part_id}"
        supplier_id = (
            cur.execute(
                "SELECT po.supplier_id FROM purchase_order po "
                "JOIN po_line pl ON pl.po_id=po.po_id "
                "WHERE pl.part_id=? ORDER BY po.po_date DESC LIMIT 1",
                (part_id,),
            ).fetchone()
            or (fallback_material_supplier,)
        )[0]
        unit_cost = (
            cur.execute(
                "SELECT unit_cost FROM po_line WHERE part_id=? ORDER BY line_id DESC LIMIT 1",
                (part_id,),
            ).fetchone()
            or (0.0,)
        )[0] or 0.0
        req = _horizon_date(f"pomrp:{part_id}", plan_start, as_of)
        po_date = plan_start  # ordered as of the plan start
        cur.execute(
            "INSERT OR IGNORE INTO purchase_order "
            "(po_id, supplier_id, po_type, po_date, required_date, status, total_cost) "
            "VALUES (?, ?, 'material', ?, ?, 'Open', ?)",
            (po_id, supplier_id, po_date.strftime(ISO), req.strftime(ISO),
             round(unit_cost * (demand_qty or 0), 2)),
        )
        if cur.rowcount:
            cur.execute(
                "INSERT INTO po_line "
                "(po_id, part_id, part_description, quantity, unit_cost, line_total) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (po_id, part_id, part_desc or part_id, demand_qty or 0, unit_cost,
                 round(unit_cost * (demand_qty or 0), 2)),
            )
            fallback_pos += 1

    conn.commit()

    # 6. Report + fail-closed validation. --------------------------------------
    print(f"  as-of date (data-derived): {as_of.strftime(ISO)}")
    print(f"  plan start (bucket M0):    {plan_start.strftime(ISO)}")
    print(f"  horizon: {buckets[0][0]} .. {buckets[-1][0]} ({eng.HORIZON_MONTHS} buckets)")
    if added_col:
        print(f"  columns added: {', '.join(added_col)}")
    print(f"  open CO lines dated (need_by/desired_release): {len(demand_updates)}")
    print(f"  outside-service WOs enriched (service_date/vendor_id): {len(os_updates)}")
    print(f"  open POs rescheduled into horizon: {len(po_reschedules)}")
    print(f"  non-closed WOs rescheduled into horizon: {len(wo_reschedules)}")
    print(f"  fallback in-horizon POs created: {fallback_pos}")

    summary = eng.validate_planning_inputs(conn)
    print(
        f"  fail-closed validation: PASS "
        f"({summary['demand_parts']} demand parts plannable in horizon)"
    )

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
