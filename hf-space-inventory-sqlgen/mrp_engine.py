"""MRP demand-supply schedule engine — horizon-aware, read-only, deterministic.

The engine nets open customer-order demand against on-hand inventory and existing
work-order / purchase-order scheduled receipts across a rolling monthly horizon,
and (in later cycles) suggests lead-time-offset planned orders.

Design invariants (shared by the migration and the Gradio tab):
  * **Data-derived AS_OF, never wall-clock.** The anchor is MAX(work_order.close_date)
    with a stable fallback, mirroring the operation-schedule backfill convention.
  * **PLAN_START = first day of the AS_OF month.** Buckets are that month plus the
    following five (six monthly buckets, "M0..M5"). Anything before PLAN_START is
    "Past Due".
  * **Deterministic.** No wall-clock, no per-run randomness.
  * **Fail closed.** Missing planning inputs raise a clear error instead of
    silently defaulting to zero.
  * **Read-only.** The engine only ever SELECTs; it never writes SQLite or the
    certified ArangoDB graph.

Cycle 1 (data foundations) uses ``compute_as_of`` / ``month_buckets`` /
``validate_planning_inputs``; the full netting grid is layered on top in a later
cycle.
"""

import calendar
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "app_schema", "manufacturing.db")

ISO = "%Y-%m-%d"
FALLBACK_AS_OF = date(2026, 6, 12)
HORIZON_MONTHS = 6

# Demand / supply status vocabularies (see replit.md "ERP planner vocabulary").
OPEN_CO_STATUS = "Open"
NONCLOSED_WO_STATUSES = ("unreleased", "firmed", "released")
OPEN_PO_STATUSES = ("Open", "Partial")


# --------------------------------------------------------------------------- #
# date helpers
# --------------------------------------------------------------------------- #
def _parse(d):
    """Parse an ISO date string (or date) to a ``date``; ``None`` when unusable."""
    if not d:
        return None
    if isinstance(d, date):
        return d
    try:
        return date.fromisoformat(str(d)[:10])
    except ValueError:
        return None


def first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    """Add ``n`` calendar months to ``d``, clamping the day to the target month."""
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


# --------------------------------------------------------------------------- #
# connection + schema helpers
# --------------------------------------------------------------------------- #
def connect(db_path: str = None) -> sqlite3.Connection:
    """Open a read-only-friendly connection (callers must not write)."""
    return sqlite3.connect(db_path or DB_PATH)


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _require_columns(conn: sqlite3.Connection, table: str, columns) -> None:
    missing = [c for c in columns if not _has_column(conn, table, c)]
    if missing:
        raise ValueError(
            f"MRP planning inputs missing on '{table}': {', '.join(missing)}. "
            "Run migrations/backfill_mrp_demand_supply.py to build the data "
            "foundation first (fail closed)."
        )


# --------------------------------------------------------------------------- #
# horizon anchor + buckets
# --------------------------------------------------------------------------- #
def compute_as_of(conn: sqlite3.Connection) -> date:
    """Data-derived as-of anchor: MAX(work_order.close_date), else the fallback.

    Uses close_date (never rewritten by the MRP backfill) so the anchor — and
    therefore every derived date — is a stable fixed point across re-runs.
    """
    row = conn.execute("SELECT MAX(close_date) FROM work_order").fetchone()
    return _parse(row[0] if row else None) or FALLBACK_AS_OF


def plan_start(as_of: date) -> date:
    """First day of the as-of month — the first planning bucket (M0)."""
    return first_of_month(as_of)


def month_buckets(as_of: date, n: int = HORIZON_MONTHS):
    """Return ``n`` monthly buckets as ``(label, start, end_exclusive)`` tuples.

    Bucket 0 is the as-of month; ``end_exclusive`` is the first day of the next
    bucket, so membership is ``start <= d < end_exclusive``.
    """
    start = plan_start(as_of)
    out = []
    for i in range(n):
        b_start = add_months(start, i)
        b_end = add_months(start, i + 1)
        out.append((b_start.strftime("%b %Y"), b_start, b_end))
    return out


def horizon_bounds(buckets):
    """(start_inclusive, end_exclusive) spanning all buckets."""
    return buckets[0][1], buckets[-1][2]


def bucket_index_for(d: date, buckets):
    """Index of the bucket containing ``d``; ``None`` if outside the horizon.

    A date before the first bucket ('Past Due') or on/after the last bucket end
    returns ``None`` — callers decide how to fold those in.
    """
    if d is None:
        return None
    for i, (_label, b_start, b_end) in enumerate(buckets):
        if b_start <= d < b_end:
            return i
    return None


# --------------------------------------------------------------------------- #
# supply / demand lookups (horizon-aware)
# --------------------------------------------------------------------------- #
def _in_clause(values):
    return ", ".join("?" for _ in values)


def has_scheduled_receipt_in_horizon(conn, part_id, buckets) -> bool:
    """True if the part has any non-closed WO or open/partial PO receipt whose
    due date (required_date) lands inside the horizon."""
    hs, he = horizon_bounds(buckets)
    hs, he = hs.isoformat(), he.isoformat()

    wo = conn.execute(
        f"""
        SELECT 1 FROM work_order
        WHERE part_id = ?
          AND status IN ({_in_clause(NONCLOSED_WO_STATUSES)})
          AND required_date IS NOT NULL
          AND date(required_date) >= ? AND date(required_date) < ?
        LIMIT 1
        """,
        (part_id, *NONCLOSED_WO_STATUSES, hs, he),
    ).fetchone()
    if wo:
        return True

    po = conn.execute(
        f"""
        SELECT 1
        FROM po_line pl
        JOIN purchase_order po ON po.po_id = pl.po_id
        WHERE pl.part_id = ?
          AND po.status IN ({_in_clause(OPEN_PO_STATUSES)})
          AND po.required_date IS NOT NULL
          AND date(po.required_date) >= ? AND date(po.required_date) < ?
        LIMIT 1
        """,
        (part_id, *OPEN_PO_STATUSES, hs, he),
    ).fetchone()
    return bool(po)


def demand_parts_in_horizon(conn, buckets):
    """Parts (with lead time + on-hand) that have open customer-order demand whose
    need_by_date lands inside the horizon. Returns list of dict rows."""
    _require_columns(conn, "customer_order_line", ["need_by_date"])
    hs, he = horizon_bounds(buckets)
    rows = conn.execute(
        """
        SELECT l.part_id,
               p.part_class,
               p.lead_time_days,
               p.on_hand_qty,
               COUNT(*)          AS demand_lines,
               SUM(l.order_qty)  AS demand_qty
        FROM customer_order_line l
        JOIN customer_order o ON o.order_id = l.order_id
        JOIN part p           ON p.part_id  = l.part_id
        WHERE o.status = ?
          AND l.need_by_date IS NOT NULL
          AND date(l.need_by_date) >= ? AND date(l.need_by_date) < ?
        GROUP BY l.part_id
        ORDER BY p.part_class, l.part_id
        """,
        (OPEN_CO_STATUS, hs.isoformat(), he.isoformat()),
    ).fetchall()
    return [
        {
            "part_id": r[0],
            "part_class": r[1],
            "lead_time_days": r[2],
            "on_hand_qty": r[3],
            "demand_lines": r[4],
            "demand_qty": r[5],
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# fail-closed validation (Cycle 1 acceptance)
# --------------------------------------------------------------------------- #
def validate_planning_inputs(conn):
    """Fail closed unless every part with demand in the horizon is plannable.

    A part is plannable when it has a positive lead time (needed to offset
    planned releases) AND a real supply basis — on-hand inventory OR a scheduled
    receipt landing in the horizon. Anything else raises ``ValueError`` with a
    per-part explanation rather than silently planning against zero.

    Returns a summary dict on success.
    """
    _require_columns(conn, "customer_order_line", ["need_by_date", "desired_release_date"])
    as_of = compute_as_of(conn)
    buckets = month_buckets(as_of)
    hs, he = horizon_bounds(buckets)

    parts = demand_parts_in_horizon(conn, buckets)
    problems = []
    for row in parts:
        part_id = row["part_id"]
        lead = row["lead_time_days"]
        on_hand = row["on_hand_qty"] or 0
        if lead is None or lead <= 0:
            problems.append(f"{part_id}: missing or non-positive lead_time_days")
            continue
        covered = on_hand > 0 or has_scheduled_receipt_in_horizon(conn, part_id, buckets)
        if not covered:
            problems.append(
                f"{part_id}: no on-hand inventory and no scheduled receipts in the horizon"
            )

    if problems:
        raise ValueError(
            "MRP planning inputs incomplete (fail closed):\n  - "
            + "\n  - ".join(problems)
        )

    return {
        "as_of": as_of,
        "horizon_start": hs,
        "horizon_end": he,
        "buckets": [b[0] for b in buckets],
        "demand_parts": len(parts),
    }


if __name__ == "__main__":
    _conn = connect()
    try:
        summary = validate_planning_inputs(_conn)
        print("MRP planning inputs OK (fail-closed validation passed).")
        print(f"  as-of (data-derived): {summary['as_of'].strftime(ISO)}")
        print(f"  horizon: {summary['buckets'][0]} .. {summary['buckets'][-1]}")
        print(f"  demand parts in horizon: {summary['demand_parts']}")
    finally:
        _conn.close()
