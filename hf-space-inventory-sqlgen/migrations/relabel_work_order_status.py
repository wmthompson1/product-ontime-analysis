"""
Migration: Relabel work_order.status to the real ERP planner vocabulary.

Supply-side work orders use four planner statuses:
  unreleased  -- planned, not yet released to the floor (no operation has started)
  firmed      -- firm planned order the planner has LOCKED; used for first lots
                 tested and recently engineered parts (extra control before release)
  released    -- released to the floor; work is in progress. Step-level progress is
                 read from operation.status / operation.close_date, never sequence_no
  closed      -- job finished and closed out

The seeders emit older invented labels (Open / Released / In Process / Complete /
Closed). This migration maps the committed manufacturing.db onto the real
vocabulary and designates a deterministic handful of not-yet-released jobs as
'firmed' (first lots / recently engineered parts).

Mapping (idempotent — also maps the new vocabulary onto itself):
  Open, unreleased, firmed   -> unreleased (base)
  Released, In Process, released -> released
  Complete, Closed, closed   -> closed
A not-yet-released job (base 'unreleased') is promoted to 'firmed' when
zlib.crc32(wo_id) % FIRMED_EVERY == 0. Because that test depends only on the stable
wo_id, re-running reproduces the identical set (a fixed point). Unknown statuses are
left untouched and reported.

Run order: this runs BEFORE migrations/backfill_operation_progress.py, which reads
work_order.status to derive operation progress. Dates (open/close/required) are not
touched. Safe to re-run.

Run once (safe to re-run):
    cd hf-space-inventory-sqlgen
    python migrations/relabel_work_order_status.py
"""

import os
import sqlite3
import zlib

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

FIRMED_EVERY = 4  # ~1 in 4 not-yet-released jobs are firmed (first lots / new parts)

# old/new label -> base real status
BASE = {
    "Open": "unreleased", "unreleased": "unreleased", "firmed": "unreleased",
    "Released": "released", "In Process": "released", "released": "released",
    "Complete": "closed", "Closed": "closed", "closed": "closed",
}


def target_status(wo_id, status):
    base = BASE.get(status)
    if base is None:
        return None  # unknown -> leave untouched
    if base == "unreleased" and zlib.crc32(wo_id.encode()) % FIRMED_EVERY == 0:
        return "firmed"
    return base


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = cur.execute("SELECT wo_id, status FROM work_order").fetchall()
    updates, counts, unknown = [], {}, {}
    for wo_id, status in rows:
        final = target_status(wo_id, status)
        if final is None:
            unknown[status] = unknown.get(status, 0) + 1
            continue
        updates.append((final, wo_id))
        counts[final] = counts.get(final, 0) + 1

    cur.executemany("UPDATE work_order SET status=? WHERE wo_id=?", updates)
    conn.commit()
    conn.close()

    print("  work_order.status now: "
          + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    if unknown:
        print("  WARNING left untouched (unknown status): "
              + ", ".join(f"{k}={unknown[k]}" for k in sorted(unknown)))
    print("Done.")


if __name__ == "__main__":
    run()
