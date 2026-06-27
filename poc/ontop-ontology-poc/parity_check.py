#!/usr/bin/env python3
"""
Parity check: virtual SPARQL graph (Ontop) vs the governed SQL semantic layer.
=============================================================================

Proves that the on-time delivery rate answered through the standards-based
virtual knowledge graph (Ontop rewriting SPARQL -> SQL over manufacturing.db)
matches, to floating-point tolerance, the number produced by SolderEngine's
assembled SQL for the same metric.

Read-only by design:
  * The live database is WAL-mode and is opened ONLY to take a read-only
    backup snapshot. Nothing ever writes to the live file.
  * Ontop and SolderEngine both run against the SAME snapshot, so the two
    engines provably see identical data.

Exit code 0 on parity, 1 on mismatch or error.
"""
import csv
import os
import sqlite3
import subprocess
import sys

POC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(POC_DIR, "..", ".."))
LIVE_DB = os.path.join(REPO_ROOT, "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db")
HF_DIR = os.path.join(REPO_ROOT, "hf-space-inventory-sqlgen")

ONTOP = os.path.join(POC_DIR, "tools", "ontop-cli-5.5.0", "ontop")
ONTOLOGY = os.path.join(POC_DIR, "ontology", "on_time_delivery.ttl")
MAPPING = os.path.join(POC_DIR, "mapping", "on_time_delivery.obda")
QUERIES = os.path.join(POC_DIR, "queries")
RESULTS = os.path.join(POC_DIR, "results")
TOOLS_TMP = os.path.join(POC_DIR, "tools", "tmp")

METRIC = "DeliveryPerformanceOps"
TOLERANCE = 1e-9


def make_snapshot():
    """Read-only backup of the live WAL-mode DB into a plain snapshot file."""
    os.makedirs(TOOLS_TMP, exist_ok=True)
    snap = os.path.join(TOOLS_TMP, "manufacturing_snapshot.db")
    for ext in ("", "-wal", "-shm"):
        p = snap + ext
        if os.path.exists(p):
            os.remove(p)
    try:
        src = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        # Fail closed: never fall back to a writable connection on the live DB.
        raise SystemExit(
            f"Refusing to run: could not open the live database read-only ({exc})."
        )
    try:
        dst = sqlite3.connect(snap)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return snap


def write_runtime_properties(snap):
    os.makedirs(RESULTS, exist_ok=True)
    p = os.path.join(RESULTS, ".runtime.properties")
    with open(p, "w") as f:
        f.write(f"jdbc.url=jdbc:sqlite:{snap}\n")
        f.write("jdbc.driver=org.sqlite.JDBC\n")
    return p


def run_sparql(props, query_file, out_csv):
    cmd = [
        ONTOP, "query",
        "-m", MAPPING,
        "-t", ONTOLOGY,
        "-p", props,
        "-q", query_file,
        "-o", out_csv,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=POC_DIR)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + "\n" + res.stderr + "\n")
        raise SystemExit(f"ontop query failed for {os.path.basename(query_file)}")
    return out_csv


def read_first_column(csv_path):
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.reader(f) if r]
    if len(rows) < 2:
        raise SystemExit(f"No result rows in {csv_path}")
    val = rows[1][0].strip()
    if "^^" in val:
        val = val.split("^^")[0]
    return float(val.strip('"'))


def solder_value(snap):
    sys.path.insert(0, HF_DIR)
    from solder_engine import SolderEngine

    engine = SolderEngine(db_path=snap)
    result = engine.assemble_metric_sql(METRIC, "sqlite")
    conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
    try:
        value = conn.execute(result.sql).fetchone()[0]
    finally:
        conn.close()
    return value, result.sql


def main():
    if not os.path.exists(ONTOP):
        raise SystemExit(
            "Ontop CLI not found. Run: python3 replit_integrations/ontop_poc_setup.py "
            "first to download the toolchain."
        )
    if not os.path.exists(LIVE_DB):
        raise SystemExit(f"Live database not found at {LIVE_DB}")

    print("Building read-only snapshot of the live database...")
    snap = make_snapshot()
    props = write_runtime_properties(snap)

    print("Running SPARQL through the Ontop virtual graph...")
    ops_csv = run_sparql(props, os.path.join(QUERIES, "on_time_rate_ops.rq"),
                         os.path.join(RESULTS, "on_time_rate_ops.csv"))
    parent_csv = run_sparql(props, os.path.join(QUERIES, "on_time_rate_parent.rq"),
                            os.path.join(RESULTS, "on_time_rate_parent.csv"))

    sparql_ops = read_first_column(ops_csv)
    sparql_parent = read_first_column(parent_csv)

    print("Running SolderEngine assembled SQL...")
    solder_rate, solder_sql = solder_value(snap)

    print()
    print("=" * 68)
    print("  ON-TIME DELIVERY RATE — PARITY CHECK")
    print("=" * 68)
    print(f"  SolderEngine assembled SQL     : {solder_rate!r}")
    print(f"  SPARQL  (Operations subproperty): {sparql_ops!r}")
    print(f"  SPARQL  (shared parent property): {sparql_parent!r}")
    print("-" * 68)
    print("  SolderEngine SQL:")
    for line in solder_sql.splitlines():
        print("    " + line)
    print("=" * 68)

    ops_ok = abs(sparql_ops - solder_rate) <= TOLERANCE
    parent_ok = abs(sparql_parent - solder_rate) <= TOLERANCE

    if ops_ok and parent_ok:
        print("  RESULT: PARITY CONFIRMED \u2014 the virtual SPARQL graph and the")
        print("          governed SQL semantic layer return the same number.")
        print("=" * 68)
        return 0

    print("  RESULT: MISMATCH")
    if not ops_ok:
        print(f"    Operations subproperty differs by {abs(sparql_ops - solder_rate)}")
    if not parent_ok:
        print(f"    Parent property differs by {abs(sparql_parent - solder_rate)}")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    sys.exit(main())
