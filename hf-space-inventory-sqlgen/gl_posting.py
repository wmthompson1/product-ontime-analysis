"""
gl_posting.py — simple synthetic GL posting functions (NO control logic).

Four posting functions, each inserting into gl_events plus the relevant
inventory ledger table(s) and gl_job_cost_detail:

  post_material_issue   RM  -> WIP   (material cost onto the job)
  post_labor            -> WIP       (labor cost onto the job)
  post_overhead         -> WIP       (burden/overhead cost onto the job)
  post_job_completion   WIP -> FG    (relieve WIP into finished goods)

Design rules (deliberate simplicity):
  * NO period close, NO reconciliation, NO validation beyond fail-closed
    argument checks. Balances are signed line amounts (+ in, - out).
  * event_date is ALWAYS caller-supplied and data-derived from the source
    document — never wall-clock.
  * Idempotency: each posting carries (source_table, source_id) and an
    event_type. If a gl_events row with the same (source_table, source_id,
    event_type) already exists, the posting is a NO-OP and returns None.
    Re-running a backfill therefore creates no duplicates.
  * Functions take an open sqlite3 connection/cursor and do NOT commit —
    transaction control belongs to the caller.

Event types written:
  RM_ISSUE (material), LABOR, BURDEN, FG_COMPLETION.
Job-cost-detail cost elements: MATERIAL, LABOR, BURDEN.
"""

import sqlite3

__all__ = [
    "post_material_issue",
    "post_labor",
    "post_overhead",
    "post_job_completion",
]


def _existing_event(cur, source_table, source_id, event_type):
    row = cur.execute(
        "SELECT event_id FROM gl_events "
        "WHERE source_table = ? AND source_id = ? AND event_type = ?",
        (source_table, str(source_id), event_type),
    ).fetchone()
    return row[0] if row else None


def _new_event(cur, job_id, event_type, amount, event_date, source_table, source_id):
    cur.execute(
        "INSERT INTO gl_events (job_id, event_type, amount, event_date, "
        "source_table, source_id) VALUES (?,?,?,?,?,?)",
        (job_id, event_type, round(amount, 2), event_date, source_table, str(source_id)),
    )
    return cur.lastrowid


def _inv_line(cur, table, event_id, job_id, part_id, amount, event_type, event_date):
    cur.execute(
        f"INSERT INTO {table} (event_id, job_id, part_id, amount, event_type, "
        "event_date) VALUES (?,?,?,?,?,?)",
        (event_id, job_id, part_id, round(amount, 2), event_type, event_date),
    )


def _cost_line(cur, event_id, job_id, amount, element, event_date):
    cur.execute(
        "INSERT INTO gl_job_cost_detail (event_id, job_id, amount, event_type, "
        "event_date) VALUES (?,?,?,?,?)",
        (event_id, job_id, round(amount, 2), element, event_date),
    )


def _check(amount, event_date):
    if amount is None or amount <= 0:
        raise ValueError(f"posting amount must be positive, got {amount!r}")
    if not event_date:
        raise ValueError("event_date is required (data-derived, never wall-clock)")


def post_material_issue(cur, job_id, part_id, amount, event_date,
                        source_table, source_id):
    """RM -> WIP: material issued from raw-materials stock onto a job."""
    _check(amount, event_date)
    if _existing_event(cur, source_table, source_id, "RM_ISSUE") is not None:
        return None
    ev = _new_event(cur, job_id, "RM_ISSUE", amount, event_date,
                    source_table, source_id)
    _inv_line(cur, "gl_raw_materials_inventory", ev, job_id, part_id,
              -amount, "RM_ISSUE", event_date)
    _inv_line(cur, "gl_wip_inventory", ev, job_id, part_id,
              amount, "RM_ISSUE", event_date)
    _cost_line(cur, ev, job_id, amount, "MATERIAL", event_date)
    return ev


def post_labor(cur, job_id, part_id, amount, event_date,
               source_table, source_id):
    """Labor cost posted into WIP for a job."""
    _check(amount, event_date)
    if _existing_event(cur, source_table, source_id, "LABOR") is not None:
        return None
    ev = _new_event(cur, job_id, "LABOR", amount, event_date,
                    source_table, source_id)
    _inv_line(cur, "gl_wip_inventory", ev, job_id, part_id,
              amount, "LABOR", event_date)
    _cost_line(cur, ev, job_id, amount, "LABOR", event_date)
    return ev


def post_overhead(cur, job_id, part_id, amount, event_date,
                  source_table, source_id):
    """Overhead (burden) cost posted into WIP for a job."""
    _check(amount, event_date)
    if _existing_event(cur, source_table, source_id, "BURDEN") is not None:
        return None
    ev = _new_event(cur, job_id, "BURDEN", amount, event_date,
                    source_table, source_id)
    _inv_line(cur, "gl_wip_inventory", ev, job_id, part_id,
              amount, "BURDEN", event_date)
    _cost_line(cur, ev, job_id, amount, "BURDEN", event_date)
    return ev


def post_job_completion(cur, job_id, part_id, amount, event_date,
                        source_table, source_id):
    """WIP -> FG: relieve accumulated job cost into finished goods."""
    _check(amount, event_date)
    if _existing_event(cur, source_table, source_id, "FG_COMPLETION") is not None:
        return None
    ev = _new_event(cur, job_id, "FG_COMPLETION", amount, event_date,
                    source_table, source_id)
    _inv_line(cur, "gl_wip_inventory", ev, job_id, part_id,
              -amount, "FG_COMPLETION", event_date)
    _inv_line(cur, "gl_finished_goods_inventory", ev, job_id, part_id,
              amount, "FG_COMPLETION", event_date)
    return ev
