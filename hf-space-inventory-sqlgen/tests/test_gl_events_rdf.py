"""
Gate-style test for the RDF event trace of the job-costing ledger
(gl_events_rdf.py).

Part A runs against a throwaway in-memory ledger: posts one document of
each of the four types through gl_posting, then proves each event class's
emitted triples (rdf:type, forJob, and the per-class flow properties)
match the Task-4 ontology, that IRIs are deterministic (derived from the
idempotency key, serialize twice -> byte-identical), and that unknown
event types fail closed.

Part B runs read-only against the live manufacturing.db and proves the
backfilled ledger yields a complete event trace: 1:1 correspondence
between gl_job_cost_detail rows and WIP-addition events, completions
relieving into finished goods, no duplicates, no unknown types.

Run:  python tests/test_gl_events_rdf.py
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "migrations"))

from gl_posting import (  # noqa: E402
    post_material_issue,
    post_labor,
    post_overhead,
    post_job_completion,
)
from gl_events_rdf import (  # noqa: E402
    LEDGER_NS,
    RDF_TYPE,
    EVENT_TYPE_TO_CLASS,
    event_iri,
    event_triples,
    fetch_event_rows,
    serialize_events,
    verify_trace_completeness,
)
from add_gl_ledger_tables import DDL  # noqa: E402

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

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


def triples_for(conn, event_type):
    rows = [r for r in fetch_event_rows(conn.cursor())
            if r["event_type"] == event_type]
    assert len(rows) == 1
    return set(event_triples(rows[0])), rows[0]


def part_a():
    print("Part A — per-class triples on an in-memory ledger")
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(DDL)

    post_material_issue(cur, "WO-1", "P-1", 100.0, "2026-01-05",
                        "material_issue", 1)
    post_labor(cur, "WO-1", "P-1", 50.0, "2026-01-06 16:00:00",
               "labor_ticket", 7)
    post_overhead(cur, "WO-1", "P-1", 25.0, "2026-01-06 16:00:00",
                  "labor_ticket", 7)
    post_job_completion(cur, "WO-1", "P-1", 175.0, "2026-01-20",
                        "work_order", "WO-1")

    job = LEDGER_NS + "Job_WO-1"

    # MaterialIssueEvent: type + forJob + consumesMaterial + addsCostToWIP.
    s = LEDGER_NS + "MaterialIssueEvent_material_issue_1"
    got, row = triples_for(conn, "RM_ISSUE")
    check("material IRI from idempotency key",
          event_iri(row["source_table"], row["source_id"], "RM_ISSUE") == s)
    check("MaterialIssueEvent triples", got == {
        (s, RDF_TYPE, LEDGER_NS + "MaterialIssueEvent"),
        (s, LEDGER_NS + "forJob", job),
        (s, LEDGER_NS + "consumesMaterial", LEDGER_NS + "RawMaterialsInventory"),
        (s, LEDGER_NS + "addsCostToWIP", LEDGER_NS + "WIPInventory"),
    }, str(got))

    # LaborApplicationEvent: type + forJob + addsCostToWIP only.
    s = LEDGER_NS + "LaborApplicationEvent_labor_ticket_7"
    got, _ = triples_for(conn, "LABOR")
    check("LaborApplicationEvent triples", got == {
        (s, RDF_TYPE, LEDGER_NS + "LaborApplicationEvent"),
        (s, LEDGER_NS + "forJob", job),
        (s, LEDGER_NS + "addsCostToWIP", LEDGER_NS + "WIPInventory"),
    }, str(got))

    # OverheadApplicationEvent: same source doc, distinct IRI via class name.
    s = LEDGER_NS + "OverheadApplicationEvent_labor_ticket_7"
    got, _ = triples_for(conn, "BURDEN")
    check("OverheadApplicationEvent triples", got == {
        (s, RDF_TYPE, LEDGER_NS + "OverheadApplicationEvent"),
        (s, LEDGER_NS + "forJob", job),
        (s, LEDGER_NS + "addsCostToWIP", LEDGER_NS + "WIPInventory"),
    }, str(got))

    # JobCompletionEvent: producesFinishedGoods, no WIP-addition property.
    s = LEDGER_NS + "JobCompletionEvent_work_order_WO-1"
    got, _ = triples_for(conn, "FG_COMPLETION")
    check("JobCompletionEvent triples", got == {
        (s, RDF_TYPE, LEDGER_NS + "JobCompletionEvent"),
        (s, LEDGER_NS + "forJob", job),
        (s, LEDGER_NS + "producesFinishedGoods",
         LEDGER_NS + "FinishedGoodsInventory"),
    }, str(got))

    # Deterministic serialization: byte-identical across runs.
    t1 = serialize_events(conn)
    t2 = serialize_events(conn)
    check("serialization deterministic", t1 == t2)
    check("no random UUIDs in output", "urn:uuid" not in t1 and t1.count(":") > 0)
    from gl_events_rdf import CLASS_FLOW_PROPERTIES
    n_expected = sum(
        2 + len(CLASS_FLOW_PROPERTIES[EVENT_TYPE_TO_CLASS[r["event_type"]]])
        for r in fetch_event_rows(conn.cursor()))
    n_stmts = sum(1 for line in t1.splitlines()
                  if line.endswith(" .") and not line.startswith("@prefix"))
    check("one triple line per expected triple", n_stmts == n_expected,
          f"{n_stmts} != {n_expected}")

    # Trace completeness passes on the clean in-memory ledger.
    stats = verify_trace_completeness(conn)
    check("in-memory trace complete", stats["events"] == 4
          and stats["cost_detail_rows"] == 3 and stats["completions"] == 1,
          str(stats))

    # Fail-closed: unknown event type rejected in serialization + check.
    cur.execute(
        "INSERT INTO gl_events (job_id, event_type, amount, event_date, "
        "source_table, source_id) VALUES ('WO-1','BOGUS',1.0,'2026-01-21',"
        "'x','1')")
    try:
        serialize_events(conn)
        check("unknown event_type fails serialization", False, "no ValueError")
    except ValueError:
        check("unknown event_type fails serialization", True)
    try:
        verify_trace_completeness(conn)
        check("unknown event_type fails completeness", False, "no ValueError")
    except ValueError:
        check("unknown event_type fails completeness", True)

    conn.close()


def part_b():
    print("Part B — backfilled ledger yields a complete event trace (live DB)")
    if not os.path.exists(DB_PATH):
        print("  SKIP  live DB not found")
        return
    conn = sqlite3.connect(DB_PATH)

    try:
        stats = verify_trace_completeness(conn)
        check("live trace complete (1:1 detail<->event)", True)
        check("live ledger has events", stats["events"] > 0, str(stats))
        check("live ledger has completions", stats["completions"] > 0, str(stats))
        print(f"        events={stats['events']} "
              f"cost_detail={stats['cost_detail_rows']} "
              f"completions={stats['completions']}")
    except ValueError as e:
        check("live trace complete (1:1 detail<->event)", False, str(e))
        conn.close()
        return

    # One event per posted source document (idempotency key is unique).
    cur = conn.cursor()
    n_keys = cur.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT source_table, source_id, "
        "event_type FROM gl_events)").fetchone()[0]
    check("one event per (source doc, type)", n_keys == stats["events"],
          f"{n_keys} keys vs {stats['events']} events")

    # Deterministic full serialization over the live ledger.
    t1 = serialize_events(conn)
    t2 = serialize_events(conn)
    check("live serialization deterministic", t1 == t2)
    for cls in ("MaterialIssueEvent", "LaborApplicationEvent",
                "OverheadApplicationEvent", "JobCompletionEvent"):
        check(f"live trace contains {cls}", f":{cls}" in t1)

    conn.close()


if __name__ == "__main__":
    part_a()
    part_b()
    print(f"\n{PASS} passed, {FAIL} failed")
    if FAIL:
        raise SystemExit(1)
    print("ALL CHECKS PASSED")
