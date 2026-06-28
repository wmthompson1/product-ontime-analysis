#!/usr/bin/env python3
"""
HTTP smoke test for the live read-only SPARQL endpoint.
=============================================================================

Proves the endpoint actually serves SPARQL over HTTP and answers the governed
number — end to end, over the wire:

  1. Take a read-only snapshot of the live DB (never writes the live file).
  2. Boot ``ontop endpoint`` on a free localhost port over the snapshot.
  3. Wait until it answers a real query.
  4. POST the on-time-rate SPARQL query over HTTP and compare the result to the
     governed value SolderEngine assembles from the SAME snapshot.
  5. POST the supplier OPTIONAL (LEFT-JOIN) query and confirm it returns rows.
  6. Tear the server down cleanly in ``finally`` and confirm no orphan process.

Exit code 0 on success, 1 on any failure. Standalone (like ``parity_check.py``
and ``rating_parity_check.py``): it needs Java + the downloaded toolchain and
boots a JVM server, so it is NOT part of ``scripts/post-merge.sh``.
"""
import os
import sys

POC_DIR = os.path.dirname(os.path.abspath(__file__))
if POC_DIR not in sys.path:
    sys.path.insert(0, POC_DIR)

import parity_check  # noqa: E402
import sparql_endpoint as ep  # noqa: E402

TOLERANCE = 1e-9
PORT_RETRIES = 3


def main():
    ep.ensure_toolchain()
    if not os.path.exists(ep.ONTOP):
        raise SystemExit(
            "Ontop CLI not found. Run: python3 replit_integrations/ontop_poc_setup.py"
        )
    if not os.path.exists(parity_check.LIVE_DB):
        raise SystemExit(f"Live database not found at {parity_check.LIVE_DB}")

    print("Building read-only snapshot of the live database...")
    snap, props = ep.build_snapshot_and_props()

    print("Computing the governed on-time rate (SolderEngine, same snapshot)...")
    governed, _sql = parity_check.solder_value(snap)

    proc = None
    ok = False
    http_rate = None
    supplier_rows = 0
    try:
        # bind-to-0 can race; retry a couple of times if the port is taken.
        last_exc = None
        for _ in range(PORT_RETRIES):
            port = ep.find_free_port()
            log_path = os.path.join(ep.RESULTS, f"endpoint_smoke_{port}.log")
            print(f"Starting SPARQL endpoint on 127.0.0.1:{port} (log: {log_path})...")
            proc = ep.start_endpoint(port, props, log_path)
            try:
                ep.wait_until_ready(port, proc)
                break
            except SystemExit as exc:
                last_exc = exc
                ep.stop_endpoint(proc)
                proc = None
        if proc is None:
            raise SystemExit(f"Could not start the endpoint: {last_exc}")
        print("Endpoint ready.\n")

        # 1) On-time delivery rate over HTTP.
        otd_query = open(os.path.join(ep.QUERIES, "on_time_rate_ops.rq")).read()
        status, body = ep.sparql_request(port, otd_query)
        if status != 200:
            raise SystemExit(f"on-time-rate query returned HTTP {status}")
        http_rate = ep.parse_csv_first_value(body)

        # 2) Supplier OPTIONAL (LEFT-JOIN) view over HTTP.
        sup_query = open(
            os.path.join(ep.QUERIES, "suppliers_optional_deliveries.rq")).read()
        status2, body2 = ep.sparql_request(port, sup_query)
        if status2 != 200:
            raise SystemExit(f"supplier OPTIONAL query returned HTTP {status2}")
        supplier_rows = ep.csv_data_row_count(body2)

        rate_ok = abs(http_rate - governed) <= TOLERANCE
        rows_ok = supplier_rows > 0

        print("=" * 68)
        print("  LIVE SPARQL ENDPOINT \u2014 HTTP SMOKE TEST")
        print("=" * 68)
        print(f"  Endpoint URL                       : {ep.endpoint_url(port)}")
        print(f"  Governed on-time rate (SolderEngine): {governed!r}")
        print(f"  On-time rate over HTTP (SPARQL)     : {http_rate!r}")
        print(f"  Rates match (tol {TOLERANCE:g})            : {rate_ok}")
        print(f"  Supplier OPTIONAL rows over HTTP    : {supplier_rows} ({rows_ok})")
        print("=" * 68)
        ok = rate_ok and rows_ok
        if ok:
            print("  RESULT: ENDPOINT SERVES THE GOVERNED NUMBER OVER HTTP")
        else:
            print("  RESULT: SMOKE TEST FAILED")
            if not rate_ok:
                print(f"    on-time rate differs by {abs(http_rate - governed)}")
            if not rows_ok:
                print("    supplier OPTIONAL query returned no rows")
        print("=" * 68)
    finally:
        ep.stop_endpoint(proc)

    orphan = proc is not None and proc.poll() is None
    if orphan:
        print("  WARNING: endpoint process did not shut down cleanly (orphan).")
    else:
        print("  Endpoint shut down cleanly (no orphan process).")

    return 0 if (ok and not orphan) else 1


if __name__ == "__main__":
    sys.exit(main())
