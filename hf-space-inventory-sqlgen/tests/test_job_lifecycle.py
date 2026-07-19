"""Gate: Job entity & lifecycle (job_lifecycle.py) — Task: Job as a first-class
semantic entity over work_order.

Run directly (gate style):  python hf-space-inventory-sqlgen/tests/test_job_lifecycle.py

Proves:
  Part 0 — ontology & binding layer:
    * ledger_events.ttl declares :WorkOrder, :WorkOrderLifecycleState, :hasLifecycleState,
      and the four state individuals whose skos:notation values are EXACTLY
      the real work_order.status vocabulary (unreleased/firmed/released/closed).
    * The governed binding map grounds ledger:WorkOrder -> work_order keyed by wo_id.
  Part A — lifecycle functions on a throwaway in-memory DB:
    * create_job registers an unreleased synthetic WO row (seeding
      conventions: next WO-%05d id, data-derived open date, real part).
    * fail-closed guards: unknown part, bad quantity, illegal transitions,
      planned orders (WO-PLN-*) never advance or complete, completion only
      from 'released', completion needs accumulated WIP, double completion
      refused.
    * complete_job posts the FG_COMPLETION flow at the data-derived close
      date and closes the row; the trace tells the full ordered story.
    * resolve_job_reference maps "job N" / "WO-XXXXX" to a wo_id and fails
      closed on unknown/ambiguous references.
  Part B — read-only against the live manufacturing.db:
    * a backfilled closed WO's lifecycle trace shows creation, >=1 cost
      event in non-decreasing date order, and exactly one completion, last.
"""

import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "migrations"))

from job_lifecycle import (  # noqa: E402
    JobLifecycleError,
    LIFECYCLE_STATES,
    advance_job,
    complete_job,
    create_job,
    job_lifecycle_trace,
    resolve_job_reference,
)
from ledger_bindings import get_ledger_binding_store  # noqa: E402
from gl_posting import post_labor, post_material_issue  # noqa: E402
from add_gl_ledger_tables import DDL  # noqa: E402

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
EVENTS_TTL = os.path.join(
    REPO, "poc", "ontop-ontology-poc", "ontology", "ledger_events.ttl"
)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def expect_error(name, fn, needle=""):
    try:
        fn()
    except JobLifecycleError as e:
        check(name, (needle in str(e)) if needle else True,
              f"message lacked {needle!r}: {e}")
        return
    check(name, False, "no JobLifecycleError raised")


# ---------------------------------------------------------------------------
def part_0():
    print("Part 0 — ontology lifecycle states + Job->work_order binding")
    with open(EVENTS_TTL, encoding="utf-8") as fh:
        ttl = fh.read()
    check(":WorkOrder declared a owl:Class",
          re.search(r"^:WorkOrder\b.*?\ba owl:Class\b", ttl, re.S | re.M) is not None)
    check(":WorkOrderLifecycleState class declared", ":WorkOrderLifecycleState" in ttl
          and re.search(r"^:WorkOrderLifecycleState\s*\n\s+a owl:Class", ttl, re.M) is not None)
    check(":hasLifecycleState domain Job range JobLifecycleState",
          re.search(r"^:hasLifecycleState.*?rdfs:domain :WorkOrder ;.*?"
                    r"rdfs:range\s+:WorkOrderLifecycleState", ttl, re.S | re.M) is not None)
    notations = set(re.findall(r'skos:notation "([a-z]+)"', ttl))
    check("state notations are EXACTLY the real WO status vocabulary",
          notations == set(LIFECYCLE_STATES), str(sorted(notations)))
    for state in ("Unreleased", "Firmed", "Released", "Closed"):
        check(f":{state}WorkOrderState individual declared",
              re.search(rf"^:{state}WorkOrderState\s*\n\s+a owl:NamedIndividual\s*,"
                        r"\s*:WorkOrderLifecycleState", ttl, re.M) is not None)

    store = get_ledger_binding_store(reload=True)
    b = store.entity_binding("ledger:WorkOrder")
    check("binding map grounds ledger:WorkOrder", b is not None)
    check("ledger:WorkOrder -> work_order keyed by wo_id",
          b is not None and b.table_name == "work_order"
          and b.key_column == "wo_id")
    check("table_for_entity lookup", store.table_for_entity("ledger:WorkOrder") == "work_order")
    rec = store.as_records()
    check("as_records carries entity_table_bindings",
          len(rec.get("entity_table_bindings", [])) == 1)


# ---------------------------------------------------------------------------
_MINI_SCHEMA = """
CREATE TABLE part (
    part_id TEXT PRIMARY KEY, part_description TEXT NOT NULL,
    active INTEGER DEFAULT 1);
CREATE TABLE work_order (
    wo_id TEXT PRIMARY KEY, workorder_type TEXT NOT NULL,
    part_id TEXT NOT NULL, part_description TEXT NOT NULL,
    quantity REAL NOT NULL, status TEXT NOT NULL,
    open_date DATE, close_date DATE);
INSERT INTO part VALUES ('P-1', 'Bracket', 1), ('P-DEAD', 'Retired', 0);
INSERT INTO work_order VALUES
  ('WO-00001', 'M', 'P-1', 'Bracket', 5, 'closed',   '2025-11-01', '2025-12-01'),
  ('WO-00002', 'M', 'P-1', 'Bracket', 5, 'released', '2025-12-10', NULL),
  ('WO-PLN-0001', 'M', 'P-1', 'Bracket', 5, 'unreleased', '2026-01-05', NULL);
"""


def part_a():
    print("Part A — lifecycle functions on an in-memory database")
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(DDL)
    cur.executescript(_MINI_SCHEMA)

    # -- create_job -------------------------------------------------------
    new_id = create_job(cur, "P-1", 3.0)
    check("create_job continues the WO-%05d sequence", new_id == "WO-00003", new_id)
    row = cur.execute(
        "SELECT status, open_date, part_description FROM work_order WHERE wo_id=?",
        (new_id,)).fetchone()
    check("new job registers unreleased", row[0] == "unreleased")
    check("open date is data-derived (latest WO activity)", row[1] == "2026-01-05",
          str(row[1]))
    check("part description copied from part master", row[2] == "Bracket")

    expect_error("unknown part fails closed",
                 lambda: create_job(cur, "P-NOPE", 1), "unknown part")
    expect_error("inactive part fails closed",
                 lambda: create_job(cur, "P-DEAD", 1), "inactive")
    expect_error("non-positive quantity fails closed",
                 lambda: create_job(cur, "P-1", 0), "positive")

    # -- resolve_job_reference ---------------------------------------------
    check('resolve "job 3"', resolve_job_reference(cur, "job 3") == "WO-00003")
    check('resolve "WO-00002"', resolve_job_reference(cur, "WO-00002") == "WO-00002")
    check('resolve "Job wo-00001" (case)', resolve_job_reference(cur, "Job wo-00001") == "WO-00001")
    expect_error("unknown numeric reference fails closed",
                 lambda: resolve_job_reference(cur, "job 99"), "no job numbered")
    expect_error("unresolvable text fails closed",
                 lambda: resolve_job_reference(cur, "the big one"), "unresolvable")

    # -- advance_job --------------------------------------------------------
    advance_job(cur, new_id, "firmed")
    advance_job(cur, new_id, "released")
    status = cur.execute("SELECT status FROM work_order WHERE wo_id=?",
                         (new_id,)).fetchone()[0]
    check("unreleased -> firmed -> released walks the real vocabulary",
          status == "released")
    expect_error("released -> firmed is illegal",
                 lambda: advance_job(cur, new_id, "firmed"), "illegal transition")
    expect_error("advance to closed is refused (ledger owns closing)",
                 lambda: advance_job(cur, new_id, "closed"), "complete_job")
    expect_error("planned order never advances",
                 lambda: advance_job(cur, "WO-PLN-0001", "released"), "planned order")

    # -- complete_job guards -------------------------------------------------
    expect_error("planned order never completes",
                 lambda: complete_job(cur, "WO-PLN-0001"), "never completable")
    expect_error("closed job refuses re-completion",
                 lambda: complete_job(cur, "WO-00001"), "already closed")
    expect_error("no accumulated WIP fails closed",
                 lambda: complete_job(cur, new_id), "no accumulated WIP")

    # -- full lifecycle: cost events then completion --------------------------
    post_material_issue(cur, new_id, "P-1", 100.0, "2026-01-06", "material_issue", 1)
    post_labor(cur, new_id, "P-1", 50.0, "2026-01-08 16:00:00", "labor_ticket", 1)
    result = complete_job(cur, new_id)
    check("completion amount = accumulated WIP", result["amount"] == 150.0,
          str(result["amount"]))
    check("close date data-derived from latest WIP event",
          result["close_date"] == "2026-01-08 16:00:00", result["close_date"])
    row = cur.execute("SELECT status, close_date FROM work_order WHERE wo_id=?",
                      (new_id,)).fetchone()
    check("work_order row closed at the derived date",
          row == ("closed", "2026-01-08 16:00:00"), str(row))
    wip = cur.execute("SELECT ROUND(COALESCE(SUM(amount),0),2) FROM gl_wip_inventory "
                      "WHERE job_id=?", (new_id,)).fetchone()[0]
    fg = cur.execute("SELECT ROUND(COALESCE(SUM(amount),0),2) FROM "
                     "gl_finished_goods_inventory WHERE job_id=?", (new_id,)).fetchone()[0]
    check("WIP relieved to 0, FG +150", wip == 0.0 and fg == 150.0, f"wip={wip} fg={fg}")
    expect_error("second completion refused (status guard)",
                 lambda: complete_job(cur, new_id), "already closed")

    # -- lifecycle trace -------------------------------------------------------
    trace = job_lifecycle_trace(cur, f"job {int(new_id.rsplit('-', 1)[-1])}")
    stages = [t["stage"] for t in trace]
    check("trace = created, cost events..., completed",
          stages == ["created", "cost_event", "cost_event", "completed"], str(stages))
    dates = [t["date"] for t in trace[1:]]
    check("trace events in non-decreasing date order",
          dates == sorted(dates), str(dates))
    check("trace completion carries the posted amount",
          trace[-1]["event_type"] == "FG_COMPLETION" and trace[-1]["amount"] == 150.0)
    conn.close()


# ---------------------------------------------------------------------------
def part_b():
    print("Part B — lifecycle trace of a backfilled closed WO (live DB, read-only)")
    if not os.path.exists(DB_PATH):
        print("  SKIP  live database not present")
        return
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT w.wo_id FROM work_order w WHERE w.status='closed' "
        "AND w.wo_id IN (SELECT job_id FROM gl_events WHERE event_type='FG_COMPLETION') "
        "ORDER BY w.wo_id LIMIT 1").fetchone()
    if row is None:
        check("a backfilled closed WO exists", False)
        conn.close()
        return
    wo_id = row[0]
    n = int(wo_id.rsplit("-", 1)[-1])
    check(f'semantic reference "job {n}" resolves to {wo_id}',
          resolve_job_reference(cur, f"job {n}") == wo_id)
    trace = job_lifecycle_trace(cur, wo_id)
    stages = [t["stage"] for t in trace]
    check("trace begins with creation", stages[0] == "created")
    check("trace has >=1 cost event", stages.count("cost_event") >= 1,
          str(stages))
    check("exactly one completion, last",
          stages.count("completed") == 1 and stages[-1] == "completed", str(stages))
    dates = [t["date"] for t in trace[1:]]
    check("cost events in non-decreasing date order", dates == sorted(dates))
    comp = trace[-1]
    wo = cur.execute("SELECT close_date FROM work_order WHERE wo_id=?",
                     (wo_id,)).fetchone()
    check("completion date matches the WO close date", comp["date"] == wo[0],
          f"{comp['date']} vs {wo[0]}")
    expect_error("planned orders never complete (live guard)",
                 lambda: complete_job(cur, "WO-PLN-0001"), "never completable")
    conn.close()


def main():
    print("== Job entity & lifecycle gate ==")
    part_0()
    part_a()
    part_b()
    print()
    if FAIL:
        print(f"RESULT: FAIL ({FAIL} failure(s), {PASS} passed)")
        sys.exit(1)
    print(f"RESULT: JOB LIFECYCLE GATE PASSED ({PASS} checks)")


if __name__ == "__main__":
    main()


