#!/usr/bin/env python3
"""
SPARQL smoke test for the job-costing ledger Ontop mapping.
=============================================================================

Starts the Ontop SPARQL endpoint with the LEDGER mapping/ontology
(mapping/job_costing_ledger.obda + ontology/job_costing_ledger.ttl) over a
read-only snapshot of the live database (same lifecycle helpers and read-only
guarantee as sparql_endpoint.py), then runs ONE smoke query per ledger table
(queries/ledger_*.rq) and compares COUNT and SUM(amount) against the governed
SQL on the SAME snapshot.

Manual verification, not a post-merge gate: it needs the JVM toolchain and
~1 min of endpoint warm-up. Run:

    python3 poc/ontop-ontology-poc/ledger_sparql_smoke.py
"""
import csv
import io
import os
import sqlite3
import sys

POC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, POC_DIR)

import sparql_endpoint as ep  # noqa: E402

LEDGER_ONTOLOGY = os.path.join(POC_DIR, "ontology", "job_costing_ledger.ttl")
LEDGER_MAPPING = os.path.join(POC_DIR, "mapping", "job_costing_ledger.obda")

# (query file, table, class label) — one smoke query per ledger table.
SMOKES = [
    ("ledger_event_count.rq", "gl_events", "GLEvent"),
    ("ledger_rm_line_total.rq", "gl_raw_materials_inventory", "RawMaterialsLine"),
    ("ledger_wip_line_total.rq", "gl_wip_inventory", "WIPLine"),
    ("ledger_fg_line_total.rq", "gl_finished_goods_inventory", "FinishedGoodsLine"),
    ("ledger_cost_line_total.rq", "gl_job_cost_detail", "JobCostLine"),
]

READINESS_QUERY = (
    "PREFIX : <http://example.org/manufacturing/jobcost#>\n"
    "SELECT ?e WHERE { ?e a :GLEvent } LIMIT 1"
)


def parse_count_sum(body):
    rows = [r for r in csv.reader(io.StringIO(body)) if r]
    if len(rows) < 2:
        raise ValueError("no data rows in SPARQL CSV result")
    def num(v):
        v = v.split("^^")[0].strip().strip('"')
        return float(v)
    return int(num(rows[1][0])), num(rows[1][1])


def main():
    ep.ensure_toolchain()
    snap, props = ep.build_snapshot_and_props()
    port = ep.find_free_port()
    log_path = os.path.join(ep.RESULTS, f"ledger_smoke_{port}.log")

    # Point the shared lifecycle helpers at the LEDGER mapping/ontology.
    ep.MAPPING = LEDGER_MAPPING
    ep.ONTOLOGY = LEDGER_ONTOLOGY
    ep.READINESS_QUERY = READINESS_QUERY

    print(f"Starting Ontop endpoint (ledger mapping) on port {port}...")
    proc = ep.start_endpoint(port, props, log_path)
    failures = 0
    try:
        ep.wait_until_ready(port, proc)
        con = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
        for fname, table, label in SMOKES:
            with open(os.path.join(ep.QUERIES, fname), encoding="utf-8") as fh:
                q = fh.read()
            status, body = ep.sparql_request(port, q)
            sp_count, sp_sum = parse_count_sum(body)
            sql_count, sql_sum = con.execute(
                f"SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM {table}"
            ).fetchone()
            ok = status == 200 and sp_count == sql_count and abs(sp_sum - sql_sum) < 1e-6
            print(
                f"  [{'PASS' if ok else 'FAIL'}] {label:<18} {fname}: "
                f"SPARQL count={sp_count} sum={sp_sum:.2f} | "
                f"SQL count={sql_count} sum={sql_sum:.2f}"
            )
            if not ok:
                failures += 1
        con.close()
    finally:
        ep.stop_endpoint(proc)

    if failures:
        print(f"RESULT: FAIL ({failures} table(s) mismatched)")
        return 1
    print("RESULT: LEDGER SPARQL SMOKE PASSED (5/5 tables queryable + parity)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
