"""job_lifecycle.py — the Job as a first-class semantic entity over work_order.

A Job maps 1:1 to the existing ``work_order`` row (Infor LN / SyteLine
semantics): this module MODELS that mapping — it never invents a parallel
table. The ontology twin is ``ledger:WorkOrder`` in
poc/ontop-ontology-poc/ontology/ledger_events.ttl (lifecycle states
Unreleased / Firmed / Released / Closed aligned to the real
``work_order.status`` vocabulary); the physical grounding is the governed
``entity_table_bindings`` entry in ledger_binding_map.json
(ledger:WorkOrder -> work_order keyed by wo_id).

API (all fail-closed, all take an open sqlite3 cursor, none commit):

  resolve_job_reference(cur, ref)   "job 42" / "42" / "WO-00042" -> wo_id
  create_job(cur, part_id, qty)     register a new synthetic WO row,
                                    status 'unreleased', data-derived open date
  advance_job(cur, ref, to_status)  unreleased -> firmed -> released only
  complete_job(cur, ref)            post the FG_COMPLETION flow
                                    (gl_posting.post_job_completion) at a
                                    data-derived close date, close the WO
  job_lifecycle_trace(cur, ref)     creation, every cost event in order,
                                    completion — the job's full story

Guards (JobLifecycleError):
  * lifecycle states are the CLOSED real vocabulary — nothing invented;
  * planned orders (WO-PLN-*) are NEVER completable or advanceable;
  * completion only from 'released', exactly once, at a close date derived
    from the job's own ledger events (never wall-clock);
  * completion requires accumulated WIP cost (> 0) in the ledger.
"""

from __future__ import annotations

import re
import sqlite3
from typing import List, Optional

from gl_posting import post_job_completion
from ledger_bindings import get_ledger_binding_store

__all__ = [
    "JobLifecycleError",
    "LIFECYCLE_STATES",
    "JOB_ENTITY_URI",
    "resolve_job_reference",
    "create_job",
    "advance_job",
    "complete_job",
    "job_lifecycle_trace",
]

JOB_ENTITY_URI = "ledger:WorkOrder"

# The CLOSED lifecycle vocabulary — exactly work_order.status, never invented.
LIFECYCLE_STATES = ("unreleased", "firmed", "released", "closed")

# Legal forward transitions short of completion (closed only via complete_job).
_ALLOWED_TRANSITIONS = {
    "unreleased": {"firmed", "released"},
    "firmed": {"released"},
}

# Planned orders are MRP proposals, never real jobs to advance or complete.
_PLANNED_PREFIX = "WO-PLN-"

# WIP-addition event types whose sum IS the job's accumulated WIP.
_WIP_EVENT_TYPES = ("RM_ISSUE", "LABOR", "BURDEN")


class JobLifecycleError(ValueError):
    """Raised on any fail-closed job lifecycle violation."""


def _job_table(store=None):
    """(table, key_column) for the Job entity from the governed binding map."""
    s = store if store is not None else get_ledger_binding_store()
    b = s.entity_binding(JOB_ENTITY_URI)
    if b is None:
        raise JobLifecycleError(
            f"{JOB_ENTITY_URI} has no entity_table_binding — the governed "
            "binding map must ground the Job before lifecycle operations"
        )
    return b.table_name, b.key_column


def _fetch_job(cur, wo_id: str):
    table, key = _job_table()
    row = cur.execute(
        f"SELECT {key}, part_id, status, open_date, close_date "
        f"FROM {table} WHERE {key} = ?",
        (wo_id,),
    ).fetchone()
    if row is None:
        raise JobLifecycleError(f"no job found for {wo_id!r}")
    return {
        "wo_id": row[0],
        "part_id": row[1],
        "status": row[2],
        "open_date": row[3],
        "close_date": row[4],
    }


def resolve_job_reference(cur, ref) -> str:
    """Resolve a semantic job reference ("job 42", "42", "WO-00042") to a wo_id.

    Uses the governed Job -> work_order binding; fails closed when the
    reference matches nothing or is ambiguous.
    """
    table, key = _job_table()
    text = str(ref).strip()
    if not text:
        raise JobLifecycleError("empty job reference")

    # Direct wo_id token (e.g. "WO-00042", "job WO-PLN-0001").
    m = re.search(r"\bWO-[A-Za-z0-9-]+\b", text, flags=re.IGNORECASE)
    if m:
        candidate = m.group(0).upper()
        row = cur.execute(
            f"SELECT {key} FROM {table} WHERE UPPER({key}) = ?", (candidate,)
        ).fetchone()
        if row is None:
            raise JobLifecycleError(f"job reference {text!r}: no such job {candidate}")
        return row[0]

    # Numeric reference ("job 42", "42") -> numeric-suffixed real WO ids.
    m = re.search(r"(\d+)\s*$", text)
    if not m:
        raise JobLifecycleError(f"unresolvable job reference {text!r}")
    n = int(m.group(1))
    matches = []
    for (wo_id,) in cur.execute(f"SELECT {key} FROM {table}"):
        # "job N" targets only the canonical WO-<number> sequence — never
        # planned (WO-PLN-*) or other prefixed synthetic families (WO-MRP-*).
        m2 = re.fullmatch(r"WO-(\d+)", wo_id)
        if m2 and int(m2.group(1)) == n:
            matches.append(wo_id)
    if not matches:
        raise JobLifecycleError(f"job reference {text!r}: no job numbered {n}")
    if len(matches) > 1:
        raise JobLifecycleError(
            f"job reference {text!r} is ambiguous: {sorted(matches)}"
        )
    return matches[0]


def _derived_open_date(cur, table: str) -> str:
    """Data-derived registration date: the latest activity date in work_order
    (MAX over open/close dates) — never wall-clock."""
    row = cur.execute(
        f"SELECT MAX(d) FROM (SELECT MAX(open_date) d FROM {table} "
        f"UNION ALL SELECT MAX(close_date) d FROM {table})"
    ).fetchone()
    if not row or not row[0]:
        raise JobLifecycleError(
            "cannot derive an open date: work_order carries no dates "
            "(pass open_date explicitly from a source document)"
        )
    return row[0]


def create_job(
    cur,
    part_id: str,
    quantity: float,
    open_date: Optional[str] = None,
    workorder_type: str = "M",
) -> str:
    """Register a new job: one synthetic work_order row, status 'unreleased'.

    Follows the established seeding conventions: zero-padded WO-%05d id
    continuing the real sequence, part must exist in the part master,
    open_date data-derived (latest work_order activity) unless supplied.
    Returns the new wo_id.
    """
    table, key = _job_table()
    if quantity is None or quantity <= 0:
        raise JobLifecycleError(f"job quantity must be positive, got {quantity!r}")
    if workorder_type not in ("M", "W"):
        raise JobLifecycleError(f"workorder_type must be M or W, got {workorder_type!r}")
    part = cur.execute(
        "SELECT part_description, COALESCE(active, 1) FROM part WHERE part_id = ?",
        (part_id,),
    ).fetchone()
    if part is None:
        raise JobLifecycleError(f"unknown part {part_id!r} — job not registered")
    if not part[1]:
        raise JobLifecycleError(f"part {part_id!r} is inactive — job not registered")
    when = open_date or _derived_open_date(cur, table)

    # Next id in the real numeric sequence (WO-00001 style; planned WO-PLN-*
    # and any non-numeric ids are outside the sequence).
    top = 0
    for (wo_id,) in cur.execute(f"SELECT {key} FROM {table}"):
        m2 = re.fullmatch(r"WO-(\d+)", wo_id)
        if m2:
            top = max(top, int(m2.group(1)))
    new_id = f"WO-{top + 1:05d}"

    cur.execute(
        f"INSERT INTO {table} ({key}, workorder_type, part_id, part_description, "
        "quantity, status, open_date) VALUES (?,?,?,?,?,?,?)",
        (new_id, workorder_type, part_id, part[0], quantity, "unreleased", when),
    )
    return new_id


def advance_job(cur, ref, to_status: str) -> str:
    """Advance a job along the real lifecycle (unreleased -> firmed -> released).

    'closed' is deliberately NOT reachable here — only complete_job closes a
    job, because closing posts the ledger completion flow.
    """
    table, key = _job_table()
    wo_id = resolve_job_reference(cur, ref)
    if wo_id.startswith(_PLANNED_PREFIX):
        raise JobLifecycleError(
            f"{wo_id} is a planned order (MRP proposal) — not advanceable"
        )
    if to_status not in LIFECYCLE_STATES:
        raise JobLifecycleError(f"unknown lifecycle state {to_status!r}")
    if to_status == "closed":
        raise JobLifecycleError("jobs close only via complete_job (ledger posting)")
    job = _fetch_job(cur, wo_id)
    allowed = _ALLOWED_TRANSITIONS.get(job["status"], set())
    if to_status not in allowed:
        raise JobLifecycleError(
            f"illegal transition {job['status']!r} -> {to_status!r} for {wo_id}"
        )
    cur.execute(
        f"UPDATE {table} SET status = ? WHERE {key} = ?", (to_status, wo_id)
    )
    return wo_id


def complete_job(cur, ref) -> dict:
    """Complete a released job: post FG_COMPLETION for its accumulated WIP at
    a data-derived close date and close the work_order row.

    Fail-closed guards: planned orders never complete; only 'released' jobs
    complete; the job must carry positive accumulated WIP in the ledger; the
    close date is the job's latest WIP event date (never wall-clock).
    """
    table, key = _job_table()
    wo_id = resolve_job_reference(cur, ref)
    if wo_id.startswith(_PLANNED_PREFIX):
        raise JobLifecycleError(
            f"{wo_id} is a planned order (MRP proposal) — never completable"
        )
    job = _fetch_job(cur, wo_id)
    if job["status"] == "closed":
        raise JobLifecycleError(f"{wo_id} is already closed")
    if job["status"] != "released":
        raise JobLifecycleError(
            f"{wo_id} is {job['status']!r} — only released jobs complete"
        )

    placeholders = ",".join("?" for _ in _WIP_EVENT_TYPES)
    amount, close_date = cur.execute(
        "SELECT COALESCE(SUM(amount), 0), MAX(event_date) FROM gl_events "
        f"WHERE job_id = ? AND event_type IN ({placeholders})",
        (wo_id, *_WIP_EVENT_TYPES),
    ).fetchone()
    if not amount or amount <= 0 or not close_date:
        raise JobLifecycleError(
            f"{wo_id} has no accumulated WIP cost in the ledger — "
            "nothing to complete"
        )
    amount = round(amount, 2)

    ev = post_job_completion(
        cur, wo_id, job["part_id"], amount, close_date, "work_order", wo_id
    )
    if ev is None:
        raise JobLifecycleError(
            f"{wo_id} already carries an FG_COMPLETION posting — refusing to "
            "close a job whose ledger says it is complete"
        )
    cur.execute(
        f"UPDATE {table} SET status = 'closed', close_date = ? WHERE {key} = ?",
        (close_date, wo_id),
    )
    return {
        "wo_id": wo_id,
        "event_id": ev,
        "amount": amount,
        "close_date": close_date,
    }


def job_lifecycle_trace(cur, ref) -> List[dict]:
    """The job's full story, in order: creation, every cost event, completion.

    Rows are dicts with a 'stage' of 'created' / 'cost_event' / 'completed'.
    Cost events come from gl_events ordered by event_date then event_id;
    the FG_COMPLETION posting is surfaced as the 'completed' stage.
    """
    wo_id = resolve_job_reference(cur, ref)
    job = _fetch_job(cur, wo_id)
    trace: List[dict] = [
        {
            "stage": "created",
            "wo_id": wo_id,
            "status": job["status"],
            "date": job["open_date"],
        }
    ]
    completed = None
    for event_id, event_type, amount, event_date in cur.execute(
        "SELECT event_id, event_type, amount, event_date FROM gl_events "
        "WHERE job_id = ? ORDER BY event_date, event_id",
        (wo_id,),
    ):
        row = {
            "stage": "cost_event",
            "wo_id": wo_id,
            "event_id": event_id,
            "event_type": event_type,
            "amount": amount,
            "date": event_date,
        }
        if event_type == "FG_COMPLETION":
            row["stage"] = "completed"
            completed = row
            continue
        trace.append(row)
    if completed is not None:
        trace.append(completed)
    return trace
