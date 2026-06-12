"""
Migration: Make operation-level job progress realistic and measurable.

Job progress for a work order is measured from operation.status (Q=Queued,
S=Started, C=Complete) and operation.close_date — NOT from sequence_no, which is
only the routing step ORDER (a gapped numeric handle). This migration derives a
coherent, sequence-ordered progress state for every operation from its parent
work_order's status, and stamps a close_date on each completed operation.

Why this is needed (the seeders left progress un-measurable / inconsistent):
  - operation.close_date was NEVER set by either seeder, so progress could not be
    measured by date at all.
  - scripts/seed_erp_synthetic.py forced EVERY operation to 'Q' regardless of the
    work order's status.
  - migrations/add_purchasing_wip_tables.py marked ops 'C' only when the whole WO
    was done, otherwise random Q/Q/S — never ordered along the routing.

Progress model (work_order.status -> its operations, ordered by sequence_no). The
work-order statuses are the real planner vocabulary set by
migrations/relabel_work_order_status.py (older labels are still accepted here so the
two migrations are order-tolerant):
  unreleased, firmed  -> not started: all ops 'Q', no close_date
  released            -> on the floor: a realistic SPREAD per work order —
                         some just released (all 'Q'), most in progress (leading
                         'C' with close_date + one current 'S' + trailing 'Q'),
                         some finished awaiting close-out (all 'C')
  closed              -> done: all ops 'C' with close_date

close_date: completed ops get dates spread in routing order (earlier step closes
earlier) inside the work order's window [open_date .. end], where end is the work
order's own close_date when present (closed jobs), else min(required_date, AS_OF).
AS_OF is the latest work_order.close_date in the DB — a fixed, data-derived "today"
so re-runs are stable (wall-clock time is intentionally NOT used). Every completed
op closes on/before its work order's close_date.

Idempotency (safe to re-run — a fixed point): status and close_date are pure
functions of (wo_id, work_order.status, operation ordinal, op count, work-order
dates), with per-work-order randomness seeded by zlib.crc32(wo_id) (NOT Python's
builtin hash(), which is salted per process). Re-running reproduces the identical
state. Updates are by operation.rowid_pk.

Run order: AFTER migrations/relabel_work_order_status.py. Safe to re-run.
    cd hf-space-inventory-sqlgen
    python migrations/backfill_operation_progress.py
"""

import os
import sqlite3
import zlib
from datetime import date, timedelta
from random import Random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# Real planner vocabulary (older invented labels kept for order-tolerance).
NOT_STARTED = {"unreleased", "firmed", "Open"}
RELEASED    = {"released", "Released", "In Process"}
DONE        = {"closed", "Closed", "Complete"}

ISO = "%Y-%m-%d"
FALLBACK_AS_OF = date(2026, 6, 12)


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


def _spread_dates(start: date, end: date, k: int):
    """k routing-ordered ISO date strings inside [start, end] (earlier step earlier,
    every date on/before end)."""
    if k <= 0:
        return []
    if end <= start:
        end = start + timedelta(days=k + 1)
    span = (end - start).days
    step = span / (k + 1)
    return [
        (start + timedelta(days=max(1, int(round(step * (j + 1)))))).strftime(ISO)
        for j in range(k)
    ]


def progress_for_wo(wstatus, n, rng):
    """Return the per-operation status list (ordered by sequence_no) for a work
    order's n operations, given the work order's status."""
    if n == 0:
        return []
    if wstatus in DONE:
        return ["C"] * n
    if wstatus in NOT_STARTED:
        return ["Q"] * n
    # released (on the floor) -> realistic spread, or unknown -> treat conservatively
    if wstatus not in RELEASED:
        return ["Q"] * n
    r = rng.random()
    if r < 0.20:                       # just released, not started yet
        completed, started = 0, False
    elif r >= 0.85:                    # all steps done, awaiting close-out
        completed, started = n, False
    else:                             # in progress
        frac = (r - 0.20) / 0.65
        completed = min(max(int(round((n - 1) * frac)), 0), n - 1)
        started = True
    out = []
    for i in range(n):
        if i < completed:
            out.append("C")
        elif started and i == completed:
            out.append("S")
        else:
            out.append("Q")
    return out


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    as_of = _parse(cur.execute("SELECT MAX(close_date) FROM work_order").fetchone()[0]) \
        or FALLBACK_AS_OF

    wo_meta = {
        r[0]: r for r in cur.execute(
            "SELECT wo_id, status, open_date, close_date, required_date FROM work_order"
        )
    }

    by_wo = {}
    for rowid_pk, wo_id, seq in cur.execute(
        "SELECT rowid_pk, wo_id, sequence_no FROM operation ORDER BY wo_id, sequence_no"
    ):
        by_wo.setdefault(wo_id, []).append(rowid_pk)

    updates = []                          # (status, close_date, rowid_pk)
    counts = {"Q": 0, "S": 0, "C": 0}
    wo_buckets = {"not started": 0, "released": 0, "closed": 0}

    for wo_id, op_rowids in by_wo.items():
        meta = wo_meta.get(wo_id)
        n = len(op_rowids)
        wstatus = meta[1] if meta else "unreleased"
        open_d = (_parse(meta[2]) if meta else None) or (as_of - timedelta(days=60))
        close_d = _parse(meta[3]) if meta else None
        req_d = _parse(meta[4]) if meta else None
        rng = _rng(wo_id)

        statuses = progress_for_wo(wstatus, n, rng)
        completed = statuses.count("C")

        if wstatus in DONE:
            wo_buckets["closed"] += 1
        elif wstatus in RELEASED:
            wo_buckets["released"] += 1
        else:
            wo_buckets["not started"] += 1

        # close_date window for the completed (leading) operations
        if completed > 0:
            if wstatus in DONE:
                end = close_d or (req_d if (req_d and req_d > open_d) else as_of)
            else:  # released — completed work happened on/before the as-of date
                end = min(req_d or as_of, as_of)
            if end <= open_d:
                end = max(as_of, open_d + timedelta(days=completed + 1))
            cdates = _spread_dates(open_d, end, completed)
        else:
            cdates = []

        ci = 0
        for i, rowid_pk in enumerate(op_rowids):
            st = statuses[i]
            cd = None
            if st == "C":
                cd = cdates[ci] if ci < len(cdates) else (close_d or as_of).strftime(ISO)
                ci += 1
            updates.append((st, cd, rowid_pk))
            counts[st] += 1

    cur.executemany(
        "UPDATE operation SET status=?, close_date=? WHERE rowid_pk=?", updates
    )
    conn.commit()

    print(f"  as-of date (data-derived): {as_of.strftime(ISO)}")
    print(f"  work orders: {wo_buckets['not started']} not started "
          f"(unreleased/firmed), {wo_buckets['released']} released, "
          f"{wo_buckets['closed']} closed")
    print(f"  operations: {counts['C']} Complete (C), {counts['S']} Started (S), "
          f"{counts['Q']} Queued (Q)")
    closed_ops = cur.execute(
        "SELECT COUNT(*) FROM operation WHERE status='C'").fetchone()[0]
    with_date = cur.execute(
        "SELECT COUNT(*) FROM operation WHERE status='C' AND close_date IS NOT NULL"
    ).fetchone()[0]
    print(f"  close_date set on {with_date}/{closed_ops} completed operations")

    print("  sample released work order routing:")
    rel = cur.execute(
        "SELECT o.wo_id FROM operation o JOIN work_order w ON w.wo_id=o.wo_id "
        "WHERE w.status='released' AND o.status='S' ORDER BY o.wo_id LIMIT 1"
    ).fetchone()
    if rel:
        for seq, ot, st, cd in cur.execute(
            "SELECT sequence_no, operation_type_id, status, close_date FROM operation "
            "WHERE wo_id=? ORDER BY sequence_no", (rel[0],)
        ):
            print(f"    {rel[0]}  seq={seq:<5} {ot or '?':<8} {st}  {cd or ''}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
