"""
Migration: Build a coherent operation routing schedule and derive the work-order
scheduled window from it.

Why this is needed (the seeders left scheduling incoherent / missing):
  - scripts/seed_erp_synthetic.py (the WO-000xx cohort) NEVER set
    operation.sched_start_date / sched_finish_date — they were all NULL.
  - migrations/add_purchasing_wip_tables.py (the WO-24xxxx cohort) used a
    placeholder per-sequence stepping (open_date + seq//10) that does NOT respect
    when the prior routing step actually closes, so a later step could be
    scheduled to start before the previous step finished.
  - work_order had no scheduled start/finish at all, so the planned WO window
    could not be read from the data.

Schedule model (per work order, operations ordered by sequence_no):
  - The first operation starts on the work order's open_date (the floor anchor;
    a data-derived fallback is used when open_date is missing).
  - Each operation's duration is derived from its hours: ceil((setup_hrs +
    run_hrs) / HOURS_PER_DAY) calendar days, with a 1-day minimum (the
    deterministic default when hours are zero/missing).
  - Each subsequent operation's scheduled start is on/after the prior step's
    scheduled finish AND on/after the prior step's actual close_date (when the
    prior step is complete), plus a small deterministic queue gap (0..MAX_QUEUE
    days, seeded by crc32(wo_id) so re-runs are stable). This guarantees the
    routing chains: a step never starts before the previous step closes.
  - A completed operation's scheduled finish is stretched to its close_date when
    the actual close ran past the planned finish, so the plan never implies the
    step finished before it actually did.

Work-order window (derived from the routing, never invented):
  - work_order.sched_start_date  = MIN(operation.sched_start_date)  (= first op start)
  - work_order.sched_finish_date = MAX(operation.sched_finish_date) (= last op finish)
  - work_order.desired_rls_date  = the planner release anchor, on/before the first
    operation start: the work order's open_date when present, else the first op
    start. Consistent across the planner vocabulary (unreleased / firmed /
    released / closed) and always populated (no NULLs).

Idempotency: every value is a pure function of (open_date, close_date, operation
hours, routing order) plus crc32(wo_id)-seeded queue gaps — a fixed point, safe
to re-run with an identical result. Wall-clock time is intentionally NOT used.
Updates are by operation.rowid_pk and work_order.wo_id. The certified ArangoDB
graph is never touched.

Run order: AFTER migrations/backfill_operation_progress.py (so operation.status
and close_date exist; schedules chain off the prior step's close). Safe to re-run.
    cd hf-space-inventory-sqlgen
    python migrations/backfill_operation_schedule.py
"""

import math
import os
import sqlite3
import zlib
from datetime import date, timedelta
from random import Random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

ISO = "%Y-%m-%d"
FALLBACK_AS_OF = date(2026, 6, 12)
HOURS_PER_DAY = 8.0          # one working day of capacity per operation-day
MAX_QUEUE = 2               # max deterministic queue gap (days) between steps


def _rng(key: str) -> Random:
    """Deterministic RNG seeded by a stable crc32 of the key (process-independent)."""
    return Random(zlib.crc32(key.encode()))


def _parse(d):
    if not d:
        return None
    try:
        return date.fromisoformat(str(d)[:10])
    except ValueError:
        return None


def _duration_days(setup_hrs, run_hrs) -> int:
    """Calendar-day duration for one operation, derived from its hours (>=1)."""
    hrs = (setup_hrs or 0.0) + (run_hrs or 0.0)
    if hrs <= 0:
        return 1
    return max(1, int(math.ceil(hrs / HOURS_PER_DAY)))


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    as_of = _parse(cur.execute("SELECT MAX(close_date) FROM work_order").fetchone()[0]) \
        or FALLBACK_AS_OF

    wo_meta = {
        r[0]: r for r in cur.execute(
            "SELECT wo_id, open_date FROM work_order"
        )
    }

    by_wo = {}
    for rowid_pk, wo_id, seq, setup_hrs, run_hrs, close_date in cur.execute(
        "SELECT rowid_pk, wo_id, sequence_no, setup_hrs, run_hrs, close_date "
        "FROM operation ORDER BY wo_id, sequence_no"
    ):
        by_wo.setdefault(wo_id, []).append(
            (rowid_pk, seq, setup_hrs, run_hrs, _parse(close_date))
        )

    op_updates = []        # (sched_start, sched_finish, rowid_pk)
    wo_updates = []        # (sched_start, sched_finish, desired_rls, wo_id)
    op_count = 0

    for wo_id, ops in by_wo.items():
        meta = wo_meta.get(wo_id)
        open_d = (_parse(meta[1]) if meta else None) or (as_of - timedelta(days=60))
        rng = _rng(wo_id)

        prev_end = None
        first_start = None
        last_finish = None
        for idx, (rowid_pk, seq, setup_hrs, run_hrs, close_d) in enumerate(ops):
            if prev_end is None:
                start = open_d                      # first routing step: floor anchor
            else:
                gap = rng.randint(0, MAX_QUEUE)     # deterministic queue time
                start = prev_end + timedelta(days=gap)
            dur = _duration_days(setup_hrs, run_hrs)
            finish = start + timedelta(days=dur)
            # A completed step's plan must not imply it finished before its actual
            # close; stretch the planned finish to the close_date when it ran over.
            if close_d and close_d > finish:
                finish = close_d
            op_updates.append((start.strftime(ISO), finish.strftime(ISO), rowid_pk))
            op_count += 1
            if first_start is None:
                first_start = start
            last_finish = finish
            # Next step starts on/after this step's finish AND its actual close.
            prev_end = max(finish, close_d) if close_d else finish

        if first_start is None:
            continue  # work order with no operations — leave its window NULL
        # The WO window is read straight off the routing it now owns.
        desired_rls = open_d if open_d <= first_start else first_start
        wo_updates.append((
            first_start.strftime(ISO),
            last_finish.strftime(ISO),
            desired_rls.strftime(ISO),
            wo_id,
        ))

    cur.executemany(
        "UPDATE operation SET sched_start_date=?, sched_finish_date=? "
        "WHERE rowid_pk=?", op_updates
    )
    cur.executemany(
        "UPDATE work_order SET sched_start_date=?, sched_finish_date=?, "
        "desired_rls_date=? WHERE wo_id=?", wo_updates
    )
    conn.commit()

    print(f"  as-of date (data-derived): {as_of.strftime(ISO)}")
    print(f"  operations scheduled: {op_count} (no NULL schedules)")
    print(f"  work orders windowed: {len(wo_updates)}")

    null_ops = cur.execute(
        "SELECT COUNT(*) FROM operation "
        "WHERE sched_start_date IS NULL OR sched_finish_date IS NULL"
    ).fetchone()[0]
    print(f"  operations still missing a schedule: {null_ops}")

    # Invariant spot-check: every step starts on/after the prior step's close.
    bad = cur.execute(
        """
        SELECT COUNT(*) FROM operation o
        JOIN operation p ON p.wo_id = o.wo_id
        WHERE p.sequence_no < o.sequence_no
          AND p.close_date IS NOT NULL
          AND o.sched_start_date < date(p.close_date)
          AND NOT EXISTS (
            SELECT 1 FROM operation m
            WHERE m.wo_id = o.wo_id AND m.sequence_no > p.sequence_no
              AND m.sequence_no < o.sequence_no)
        """
    ).fetchone()[0]
    print(f"  chain violations (start before prior step close): {bad}")

    print("  sample routing schedule:")
    sample = cur.execute(
        "SELECT wo_id FROM work_order WHERE status='closed' ORDER BY wo_id LIMIT 1"
    ).fetchone()
    if sample:
        for seq, ss, sf, cd in cur.execute(
            "SELECT sequence_no, sched_start_date, sched_finish_date, close_date "
            "FROM operation WHERE wo_id=? ORDER BY sequence_no", (sample[0],)
        ):
            print(f"    {sample[0]}  seq={seq:<5} {ss} -> {sf}  close={cd or ''}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
