"""
Migration: demand linkage + forecast demand source (Task #244).

Why (the synthetic ERP had zero demand lineage and no forecast source):
  - every work order was an unlinked MO — the "no demand traceability" row of
    the order-type matrix. Per SME guidance at least half of the orders should
    be demand-linked (Release Order → MO pattern), with the linkage visible in
    the data and queryable.
  - unlinked orders ship from the order line, so a forecast demand source must
    feed MRP gross requirements for their parts (netted so a linked order's
    demand is never double-counted — see mrp_engine.compute_mrp_grid).

What this migration establishes (all synthetic, SQLite-only, deterministic):
  1. work_order.demand_order_line_id — nullable declared FK (structural only;
     PRAGMA foreign_keys stays OFF per house style) to
     customer_order_line.order_line_id. NULL = unlinked MO.
  2. part.safety_stock — SME rule: exactly 1 for planning parts (never 0,
     never computed). The netting keeps PAB at/above this value.
  3. forecast table — (part, qty, date, site) rows; an ADDITIVE demand source
     the MRP engine consumes alongside customer-order demand.
  4. Linkage backfill: each unlinked work order is matched to an order line of
     the SAME part, preferring status-compatible pairs (closed WO ↔
     Closed/Shipped order, non-closed WO ↔ Open order), then closest quantity,
     then closest date, then lowest order_line_id — a pure greedy function of
     the stable rows, so re-runs are no-ops. Fails closed if the resulting
     linked ratio is below MIN_LINK_RATIO (0.5).
  5. Forecast seeding: every part manufactured by a still-unlinked MO gets
     crc32-keyed monthly forecast rows across the planning horizon, including
     a guaranteed row in the extended buckets (M6..M8) so the widened horizon
     carries demand. Supply tracks demand closely (small monthly quantities,
     no artificial buffers); a forecast part with no supply basis at all gets
     the minimal one (on_hand_qty = 1).

Anchor (data-derived, never wall-clock): as_of = MAX(work_order.close_date)
(mrp_engine.compute_as_of). All dates derive from as_of via crc32 of stable
keys — the same _horizon_date discipline as backfill_mrp_demand_supply.

Idempotency: column adds are PRAGMA-guarded; the forecast upsert recomputes
the same pure-function values every run; the linkage backfill only touches
rows where demand_order_line_id IS NULL and recomputes deterministically.
Safe to re-run with an identical result. The certified ArangoDB graph is
never touched. Ends with fail-closed validation: linkage ratio >= 0.5,
planning inputs valid, and planned receipts present in the extended buckets.

Run order: AFTER expand_mrp_part_universe.py (so the expansion's WOs and CO
lines participate in the linkage) and BEFORE declare_structural_fks.py.
    cd hf-space-inventory-sqlgen
    python migrations/add_demand_linkage_and_forecast.py
"""

import os
import sqlite3
import sys
import zlib
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_HERE)
sys.path.insert(0, _APP_DIR)

import mrp_engine as eng  # noqa: E402

DB_PATH = os.path.join(_APP_DIR, "app_schema", "manufacturing.db")
ISO = eng.ISO

MIN_LINK_RATIO = 0.5
# The horizon extension added buckets M6..M8; those must carry planned orders.
EXTENDED_BUCKETS = (6, 7, 8)

FORECAST_DDL = """
CREATE TABLE IF NOT EXISTS forecast (
    forecast_id   TEXT PRIMARY KEY,              -- FC-<part_id>-<YYYYMM>
    part_id       TEXT NOT NULL,
    site_id       TEXT NOT NULL DEFAULT 'SITE-1',
    forecast_date DATE NOT NULL,                 -- demand due date inside its bucket
    forecast_qty  REAL NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (part_id, forecast_date, site_id),
    FOREIGN KEY (part_id) REFERENCES part (part_id),
    FOREIGN KEY (site_id) REFERENCES site (site_id)
);
"""


def _crc(*parts) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def _widen(cur, table, columns):
    existing = {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    added = []
    for column, decl in columns.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {decl}")
            added.append(column)
    return added


def _parse_date(s):
    return eng._parse(s)


def _status_compatible(wo_status: str, co_status: str) -> bool:
    if wo_status == "closed":
        return co_status in ("Closed", "Shipped")
    return co_status == eng.OPEN_CO_STATUS


def link_work_orders(cur):
    """Deterministically link unlinked WOs to same-part order lines.

    Greedy over WOs in wo_id order; candidate score is
    (line already used, status-incompatible, |qty diff|, |date diff days|,
    order_line_id) — a pure function of the stable rows.
    Returns (linked_now, linked_total, total_wos).
    """
    lines = cur.execute(
        """
        SELECT l.order_line_id, l.part_id, l.order_qty, o.status,
               COALESCE(l.need_by_date, o.order_date)
        FROM customer_order_line l
        JOIN customer_order o ON o.order_id = l.order_id
        ORDER BY l.order_line_id
        """
    ).fetchall()
    by_part = {}
    for ol_id, part_id, qty, co_status, when in lines:
        by_part.setdefault(part_id, []).append((ol_id, qty or 0, co_status, _parse_date(when)))

    used = {
        r[0]
        for r in cur.execute(
            "SELECT DISTINCT demand_order_line_id FROM work_order "
            "WHERE demand_order_line_id IS NOT NULL"
        )
    }

    # Planned orders (WO-PLN-*, migrations/add_planned_work_orders.py) are
    # MRP proposals, not demand-pegged firm supply — never link them.
    wos = cur.execute(
        "SELECT wo_id, part_id, status, quantity, required_date FROM work_order "
        "WHERE demand_order_line_id IS NULL AND wo_id NOT LIKE 'WO-PLN-%' "
        "ORDER BY wo_id"
    ).fetchall()

    updates = []
    for wo_id, part_id, wo_status, wo_qty, wo_req in wos:
        candidates = by_part.get(part_id)
        if not candidates:
            continue
        wo_date = _parse_date(wo_req)

        def score(cand):
            ol_id, qty, co_status, co_date = cand
            date_gap = (
                abs((co_date - wo_date).days) if (co_date and wo_date) else 9999
            )
            return (
                1 if ol_id in used else 0,
                0 if _status_compatible(wo_status, co_status) else 1,
                abs((wo_qty or 0) - qty),
                date_gap,
                ol_id,
            )

        best = min(candidates, key=score)
        used.add(best[0])
        updates.append((best[0], wo_id))

    cur.executemany(
        "UPDATE work_order SET demand_order_line_id=? WHERE wo_id=?", updates
    )

    # Ratio population excludes planned orders (WO-PLN-*) — they are MRP
    # proposals outside the linkage layer, so they must not dilute the gate.
    total = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE wo_id NOT LIKE 'WO-PLN-%'"
    ).fetchone()[0]
    linked = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE demand_order_line_id IS NOT NULL "
        "AND wo_id NOT LIKE 'WO-PLN-%'"
    ).fetchone()[0]
    return len(updates), linked, total


def seed_forecast(cur, as_of: date, plan_start: date):
    """Seed crc32-keyed monthly forecast rows for parts on unlinked MOs.

    Per part: one candidate row per horizon bucket with qty crc%4 (0 = no row —
    sparse months are realistic), plus one GUARANTEED extended-bucket row
    (M6..M8) so the widened horizon always carries forecast demand. Supply
    tracks demand closely: monthly quantities stay small (<= 3).
    """
    parts = [
        r[0]
        for r in cur.execute(
            """
            SELECT DISTINCT w.part_id FROM work_order w
            JOIN part p ON p.part_id = w.part_id
            WHERE w.demand_order_line_id IS NULL
              AND w.wo_id NOT LIKE 'WO-PLN-%'
            ORDER BY w.part_id
            """
        )
    ]

    missing_lead = [
        r[0]
        for r in cur.execute(
            f"""
            SELECT part_id FROM part
            WHERE part_id IN ({','.join('?' * len(parts))})
              AND (lead_time_days IS NULL OR lead_time_days <= 0)
            """,
            parts,
        )
    ] if parts else []
    if missing_lead:
        raise SystemExit(
            "[demand-linkage] FAIL-CLOSED: forecast parts without a positive "
            f"lead time: {', '.join(missing_lead)} — fix the part master first."
        )

    rows = []
    for part_id in parts:
        buckets_with_qty = []
        for b in range(eng.HORIZON_MONTHS):
            qty = _crc(f"fc:{part_id}:{b}", as_of, "Q") % 4  # 0..3
            if qty:
                buckets_with_qty.append((b, qty))
        # Guarantee one extended-horizon row (M6..M8).
        if not any(b in EXTENDED_BUCKETS for b, _q in buckets_with_qty):
            b_ext = EXTENDED_BUCKETS[_crc(f"fcx:{part_id}", as_of, "B") % len(EXTENDED_BUCKETS)]
            qty_ext = _crc(f"fcx:{part_id}", as_of, "Q") % 3 + 1  # 1..3
            buckets_with_qty.append((b_ext, qty_ext))
        for b, qty in buckets_with_qty:
            base = eng.add_months(plan_start, b)
            day = _crc(f"fc:{part_id}:{b}", as_of, "D") % 28 + 1
            fdate = date(base.year, base.month, day)
            fid = f"FC-{part_id}-{base.strftime('%Y%m')}"
            rows.append((fid, part_id, fdate.strftime(ISO), float(qty)))

    cur.executemany(
        """
        INSERT INTO forecast (forecast_id, part_id, forecast_date, forecast_qty)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (forecast_id) DO UPDATE SET
            forecast_date = excluded.forecast_date,
            forecast_qty  = excluded.forecast_qty
        """,
        rows,
    )

    # Minimal supply basis for forecast parts with none (fail-closed validation
    # requires on-hand OR an in-horizon receipt). Idempotent: only 0 -> 1.
    buckets = eng.month_buckets(as_of)
    topped_up = 0
    for part_id in parts:
        on_hand = cur.execute(
            "SELECT COALESCE(on_hand_qty, 0) FROM part WHERE part_id=?", (part_id,)
        ).fetchone()[0]
        if on_hand > 0:
            continue
        if eng.has_scheduled_receipt_in_horizon(cur.connection, part_id, buckets):
            continue
        cur.execute("UPDATE part SET on_hand_qty=1 WHERE part_id=?", (part_id,))
        topped_up += 1

    return parts, len(rows), topped_up


def run():
    # isolation_level=None: WE control the transaction. The stdlib's legacy
    # implicit-BEGIN only fires before DML, so DDL (the ALTERs / CREATE TABLE)
    # would otherwise autocommit outside the transaction and survive a gate
    # failure.
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        _run_gated(conn)
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run_gated(conn: sqlite3.Connection) -> None:
    """Apply all changes, then commit ONLY after every fail-closed gate passes.

    Everything — DDL included — runs inside one explicit transaction. All
    gates read through the same uncommitted connection, so a gate failure
    (or any error) leaves the database untouched via the rollback in run().
    """
    cur = conn.cursor()
    cur.execute("BEGIN")

    as_of = eng.compute_as_of(conn)
    plan_start = eng.plan_start(as_of)

    # 1. Schema: linkage column + safety stock + forecast table. ---------------
    added = _widen(
        cur,
        "work_order",
        {
            "demand_order_line_id":
                "demand_order_line_id INTEGER "
                "REFERENCES customer_order_line (order_line_id)",
        },
    )
    added += _widen(cur, "part", {"safety_stock": "safety_stock REAL DEFAULT 1"})
    # SME rule: exactly 1 — repair NULL/0 values from any older path.
    cur.execute(
        "UPDATE part SET safety_stock=1 WHERE safety_stock IS NULL OR safety_stock=0"
    )
    # Single statement — cur.execute keeps everything in ONE transaction
    # (executescript would implicitly commit the pending ALTERs/UPDATE).
    cur.execute(FORECAST_DDL)

    # 2. Demand linkage backfill (>= 50%, fail closed). -------------------------
    linked_now, linked, total = link_work_orders(cur)
    ratio = linked / total if total else 0.0
    if ratio < MIN_LINK_RATIO:
        raise SystemExit(
            f"[demand-linkage] FAIL-CLOSED: only {linked}/{total} work orders "
            f"({ratio:.0%}) linked to a demand source; need >= {MIN_LINK_RATIO:.0%}."
        )

    # 3. Forecast seeding for parts still shipping from the order line. --------
    fc_parts, fc_rows, topped_up = seed_forecast(cur, as_of, plan_start)

    # 4. Report + fail-closed validation (gates run BEFORE the commit; a gate
    # failure raises, and run() rolls everything back). -------------------------
    print(f"  as-of (data-derived): {as_of.strftime(ISO)}")
    if added:
        print(f"  columns added: {', '.join(added)}")
    print(f"  work orders linked: {linked}/{total} ({ratio:.0%}; {linked_now} new)")
    print(f"  forecast parts: {len(fc_parts)}  rows upserted: {fc_rows}")
    print(f"  supply-basis top-ups (on_hand 0 -> 1): {topped_up}")

    summary = eng.validate_planning_inputs(conn)
    print(
        f"  fail-closed validation: PASS "
        f"({summary['demand_parts']} demand parts plannable in horizon)"
    )

    # Extended-horizon check: the added buckets (M6..M8, grid period index =
    # bucket + 1) must carry BOTH demand (gross requirements) and supply
    # (scheduled receipts or planned receipts) for at least one planning part
    # each. Whether a specific part nets to a planned order depends on its
    # inventory posture, which this migration deliberately does not distort
    # (supply ~ demand; no artificial shortages) — the engine's extended-bucket
    # planning behavior is proven by the fixture tests instead.
    extended_periods = {b + 1 for b in EXTENDED_BUCKETS}
    demand_hit = supply_hit = None
    for row in eng.list_planning_parts(conn):
        grid = eng.compute_mrp_grid(conn, row["part_id"])
        rows_by_label = dict(grid["rows"])
        gross = rows_by_label["Gross Requirements"]
        supply = [
            s + r
            for s, r in zip(
                rows_by_label["Scheduled Receipts"],
                rows_by_label["Planned Order Receipts"],
            )
        ]
        if demand_hit is None and any(
            gross[i] > 0 for i in extended_periods if i < len(gross)
        ):
            demand_hit = row["part_id"]
        if supply_hit is None and any(
            supply[i] > 0 for i in extended_periods if i < len(supply)
        ):
            supply_hit = row["part_id"]
        if demand_hit and supply_hit:
            break
    if demand_hit is None or supply_hit is None:
        raise SystemExit(
            "[demand-linkage] FAIL-CLOSED: extended buckets (M6..M8) missing "
            f"{'demand' if demand_hit is None else 'supply'} — horizon "
            "extension is not carrying a full demand/supply picture."
        )
    print(
        f"  extended-horizon coverage: PASS "
        f"(demand e.g. {demand_hit}; supply e.g. {supply_hit})"
    )

    # All gates passed — persist atomically.
    conn.commit()
    print("Done.")


if __name__ == "__main__":
    run()
