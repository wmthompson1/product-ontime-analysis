"""
gl_events_rdf.py — RDF event trace for the job-costing ledger.

Renders persisted gl_events rows as RDF triples matching the Task-4 event
ontology (poc/ontop-ontology-poc/ontology/ledger_events.ttl, namespace
http://example.org/manufacturing/ledger#):

  * Each gl_events row becomes one event instance whose rdf:type is the
    ontology class mapped 1:1 from the persisted event_type:
        RM_ISSUE      -> MaterialIssueEvent
        LABOR         -> LaborApplicationEvent
        BURDEN        -> OverheadApplicationEvent
        FG_COMPLETION -> JobCompletionEvent
  * Flow properties per class (exactly the ontology's vocabulary):
        forJob                 every event -> its Job (work order)
        consumesMaterial       MaterialIssueEvent -> :RawMaterialsInventory
        addsCostToWIP          WIP-addition events -> :WIPInventory
        producesFinishedGoods  JobCompletionEvent -> :FinishedGoodsInventory
  * IRIs are DETERMINISTIC, derived from the posting idempotency key
    (source_table, source_id, event_type) — never random UUIDs, so two
    serializations of the same ledger are byte-identical.

Also provides verify_trace_completeness(): a fail-closed check that the
backfilled ledger yields a complete event trace — every gl_job_cost_detail
row belongs to exactly one WIP-addition event and vice versa, every
completion event relieves into finished goods, no unknown event types, and
no duplicate idempotency keys.

Read-only: never writes to the database.
"""

import re
import sqlite3

LEDGER_NS = "http://example.org/manufacturing/ledger#"

# Persisted gl_events.event_type -> RDF class local name (Task-4 ontology).
EVENT_TYPE_TO_CLASS = {
    "RM_ISSUE": "MaterialIssueEvent",
    "LABOR": "LaborApplicationEvent",
    "BURDEN": "OverheadApplicationEvent",
    "FG_COMPLETION": "JobCompletionEvent",
    "CUSTOMER_SHIPMENT": "CustomerShipmentEvent",
    "CASH_RECEIPT": "CashReceiptEvent",
}

# Flow properties emitted per RDF class (besides rdf:type and forJob).
CLASS_FLOW_PROPERTIES = {
    "MaterialIssueEvent": [
        ("consumesMaterial", "RawMaterialsInventory"),
        ("addsCostToWIP", "WIPInventory"),
    ],
    "LaborApplicationEvent": [("addsCostToWIP", "WIPInventory")],
    "OverheadApplicationEvent": [("addsCostToWIP", "WIPInventory")],
    "JobCompletionEvent": [("producesFinishedGoods", "FinishedGoodsInventory")],
    "CustomerShipmentEvent": [("shipsFinishedGoods", "FinishedGoodsInventory")],
    "CashReceiptEvent": [("collectsAccountsReceivable", "AccountsReceivable")],
}

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def _slug(value):
    """IRI-safe local-name fragment: replace anything unusual with '_'."""
    return _SAFE.sub("_", str(value))


def event_iri(source_table, source_id, event_type):
    """Deterministic event-instance IRI from the posting idempotency key."""
    cls = EVENT_TYPE_TO_CLASS.get(event_type)
    if cls is None:
        raise ValueError(f"unknown gl_events event_type: {event_type!r}")
    return f"{LEDGER_NS}{cls}_{_slug(source_table)}_{_slug(source_id)}"


def job_iri(job_id):
    """Deterministic Job (work order) IRI."""
    return f"{LEDGER_NS}Job_{_slug(job_id)}"


def event_triples(row):
    """
    Triples for one gl_events row.

    row: mapping with keys job_id, event_type, source_table, source_id.
    Returns a list of (subject, predicate, object) full-IRI triples.
    """
    event_type = row["event_type"]
    cls = EVENT_TYPE_TO_CLASS.get(event_type)
    if cls is None:
        raise ValueError(f"unknown gl_events event_type: {event_type!r}")
    subject = event_iri(row["source_table"], row["source_id"], event_type)
    triples = [
        (subject, RDF_TYPE, LEDGER_NS + cls),
        (subject, LEDGER_NS + "forJob", job_iri(row["job_id"])),
    ]
    for prop, target in CLASS_FLOW_PROPERTIES[cls]:
        triples.append((subject, LEDGER_NS + prop, LEDGER_NS + target))
    return triples


def fetch_event_rows(cur):
    """All gl_events rows in deterministic order (event_id)."""
    cur.execute(
        "SELECT event_id, job_id, event_type, amount, event_date, "
        "source_table, source_id FROM gl_events ORDER BY event_id"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def serialize_events(conn):
    """
    Render every gl_events row as Turtle. Deterministic: same ledger in,
    byte-identical Turtle out.
    """
    cur = conn.cursor()
    lines = [
        f"@prefix : <{LEDGER_NS}> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "",
    ]

    def qname(iri):
        if iri == RDF_TYPE:
            return "rdf:type"
        if iri.startswith(LEDGER_NS):
            return ":" + iri[len(LEDGER_NS):]
        return f"<{iri}>"

    for row in fetch_event_rows(cur):
        for s, p, o in event_triples(row):
            lines.append(f"{qname(s)} {qname(p)} {qname(o)} .")
    return "\n".join(lines) + "\n"


def verify_trace_completeness(conn):
    """
    Fail-closed proof that the persisted ledger yields a complete event
    trace. Raises ValueError on the first gap; returns a stats dict on
    success.
    """
    cur = conn.cursor()
    problems = []

    unknown = cur.execute(
        "SELECT COUNT(*) FROM gl_events WHERE event_type NOT IN "
        "('RM_ISSUE','LABOR','BURDEN','FG_COMPLETION','CUSTOMER_SHIPMENT','CASH_RECEIPT')"
    ).fetchone()[0]
    if unknown:
        problems.append(f"{unknown} gl_events rows with unknown event_type")

    dupes = cur.execute(
        "SELECT COUNT(*) FROM (SELECT source_table, source_id, event_type "
        "FROM gl_events GROUP BY source_table, source_id, event_type "
        "HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    if dupes:
        problems.append(f"{dupes} duplicate (source_table, source_id, event_type) keys")

    # 1:1 — every cost-detail row belongs to exactly one WIP-addition event.
    orphan_detail = cur.execute(
        "SELECT COUNT(*) FROM gl_job_cost_detail d LEFT JOIN gl_events e "
        "ON e.event_id = d.event_id WHERE e.event_id IS NULL"
    ).fetchone()[0]
    if orphan_detail:
        problems.append(f"{orphan_detail} gl_job_cost_detail rows without an event")

    multi_detail = cur.execute(
        "SELECT COUNT(*) FROM (SELECT event_id FROM gl_job_cost_detail "
        "GROUP BY event_id HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    if multi_detail:
        problems.append(f"{multi_detail} events carrying more than one cost-detail row")

    # 1:1 — every WIP-addition event has exactly one cost-detail row.
    missing_detail = cur.execute(
        "SELECT COUNT(*) FROM gl_events e LEFT JOIN gl_job_cost_detail d "
        "ON d.event_id = e.event_id WHERE e.event_type IN "
        "('RM_ISSUE','LABOR','BURDEN') AND d.event_id IS NULL"
    ).fetchone()[0]
    if missing_detail:
        problems.append(f"{missing_detail} WIP-addition events without a cost-detail row")

    # Completions never carry cost detail; each relieves into finished goods.
    completion_detail = cur.execute(
        "SELECT COUNT(*) FROM gl_events e JOIN gl_job_cost_detail d "
        "ON d.event_id = e.event_id WHERE e.event_type = 'FG_COMPLETION'"
    ).fetchone()[0]
    if completion_detail:
        problems.append(f"{completion_detail} completion events carrying cost detail")

    completion_no_fg = cur.execute(
        "SELECT COUNT(*) FROM gl_events e LEFT JOIN gl_finished_goods_inventory f "
        "ON f.event_id = e.event_id WHERE e.event_type = 'FG_COMPLETION' "
        "AND f.event_id IS NULL"
    ).fetchone()[0]
    if completion_no_fg:
        problems.append(
            f"{completion_no_fg} completion events without a finished-goods line"
        )

    if problems:
        raise ValueError("event trace incomplete: " + "; ".join(problems))

    return {
        "events": cur.execute("SELECT COUNT(*) FROM gl_events").fetchone()[0],
        "cost_detail_rows": cur.execute(
            "SELECT COUNT(*) FROM gl_job_cost_detail"
        ).fetchone()[0],
        "completions": cur.execute(
            "SELECT COUNT(*) FROM gl_events WHERE event_type='FG_COMPLETION'"
        ).fetchone()[0],
    }


if __name__ == "__main__":
    import os

    db = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "app_schema", "manufacturing.db"
    )
    conn = sqlite3.connect(db)
    stats = verify_trace_completeness(conn)
    print(f"trace complete: {stats}")
    print(serialize_events(conn)[:2000])
