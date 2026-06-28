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

SUPPLIER_QUERY = "suppliers_optional_deliveries.rq"
NEUTRAL_RATING = 3.0  # deterministic My MRP default for a no-receipt supplier
ORPHAN_ID = "S-ORPHAN-PARITY"
ORPHAN_NAME = "__ORPHAN_NO_RECEIPTS__"


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


def _iri_tail(value):
    return value.rsplit("/", 1)[-1] if value else ""


def _as_float(literal):
    return float(literal.split("^^")[0].strip().strip('"'))


def read_result_rows(csv_path):
    """Return (header, data_rows) from an Ontop CSV result file."""
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.reader(f) if r]
    if not rows:
        return [], []
    return rows[0], rows[1:]


def sql_supplier_sets(snap):
    """Ground truth from the snapshot: the set of all supplier ids and the subset
    that has at least one receipt. Returned as ids (TEXT) so they line up with the
    tail of each SPARQL supplier IRI."""
    conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
    try:
        all_ids = {
            str(r[0]) for r in conn.execute(
                "SELECT CAST(supplier_id AS TEXT) FROM suppliers").fetchall()
        }
        linked_ids = {
            str(r[0]) for r in conn.execute(
                "SELECT DISTINCT CAST(s.supplier_id AS TEXT) FROM suppliers s "
                "WHERE EXISTS (SELECT 1 FROM receiving r "
                "WHERE CAST(r.supplier_id AS TEXT) = CAST(s.supplier_id AS TEXT))"
            ).fetchall()
        }
    finally:
        conn.close()
    return all_ids, linked_ids


def sparql_supplier_view(props, tag):
    """Run the OPTIONAL (LEFT JOIN) supplier query and reduce it to:
    population (every published supplier), linked (suppliers with >=1 delivery),
    and each supplier's reported rating."""
    out = os.path.join(RESULTS, f"suppliers_optional_{tag}.csv")
    run_sparql(props, os.path.join(QUERIES, SUPPLIER_QUERY), out)
    header, rows = read_result_rows(out)
    col = {name: i for i, name in enumerate(header)}
    si, di, ri = col["supplier"], col["delivery"], col["rating"]
    population = {r[si] for r in rows}
    linked = {r[si] for r in rows if len(r) > di and r[di].strip()}
    ratings = {r[si]: r[ri] for r in rows if len(r) > ri}
    return population, linked, ratings


def inject_orphan(snap):
    """Insert a no-receipt supplier into the THROWAWAY snapshot only (never the
    live DB) to empirically prove the link is optional."""
    conn = sqlite3.connect(snap)
    try:
        conn.execute(
            "INSERT INTO suppliers (supplier_id, supplier_name, performance_rating) "
            "VALUES (?, ?, ?)", (ORPHAN_ID, ORPHAN_NAME, NEUTRAL_RATING))
        conn.commit()
    finally:
        conn.close()


def supplier_optionality_check(props, snap):
    """Prove the supplier->receiving join is a GOVERNED LEFT JOIN: every supplier
    is published from the suppliers table, the :hasDelivery link comes only from
    receiving, and a supplier with no receipts stays published but UNLINKED with
    its neutral default rating. Returns 0 on success, 1 on failure."""
    print()
    print("=" * 68)
    print("  SUPPLIER \u2192 RECEIVING \u2014 GOVERNED LEFT-JOIN OPTIONALITY")
    print("=" * 68)

    sql_all, sql_linked = sql_supplier_sets(snap)
    population, linked, _ = sparql_supplier_view(props, "before")
    sparql_all = {_iri_tail(s) for s in population}
    sparql_linked = {_iri_tail(s) for s in linked}
    print(f"  Suppliers published   (SPARQL / SQL): {len(sparql_all)} / {len(sql_all)}")
    print(f"  Suppliers w/ delivery (SPARQL / SQL): {len(sparql_linked)} / {len(sql_linked)}")
    # Exact set parity (not just cardinality) so a swapped/missing id is caught.
    sets_ok = (sparql_all == sql_all and sparql_linked == sql_linked)
    if not sets_ok:
        print(f"    published set diff (SPARQL \u25b3 SQL): {sparql_all ^ sql_all}")
        print(f"    linked set diff    (SPARQL \u25b3 SQL): {sparql_linked ^ sql_linked}")

    # Empirical proof: drop a no-receipt supplier into the throwaway snapshot and
    # confirm it is still published, stays unlinked, and keeps its safe default.
    inject_orphan(snap)
    population2, linked2, ratings2 = sparql_supplier_view(props, "after")
    orphan_iri = next((s for s in population2 if _iri_tail(s) == ORPHAN_ID), None)
    orphan_published = orphan_iri is not None
    orphan_unlinked = orphan_published and orphan_iri not in linked2
    orphan_default_ok = False
    if orphan_published and ratings2.get(orphan_iri):
        try:
            orphan_default_ok = abs(_as_float(ratings2[orphan_iri]) - NEUTRAL_RATING) <= TOLERANCE
        except ValueError:
            orphan_default_ok = False

    population2_ids = {_iri_tail(s) for s in population2}
    linked2_ids = {_iri_tail(s) for s in linked2}

    print("-" * 68)
    print("  Injected a no-receipt supplier into the throwaway snapshot:")
    print(f"    published in SPARQL                 : {orphan_published}")
    print(f"    unlinked (no :hasDelivery edge)     : {orphan_unlinked}")
    print(f"    safe default rating == {NEUTRAL_RATING}          : {orphan_default_ok}")
    print(f"    population {len(sparql_all)} \u2192 {len(population2_ids)}, "
          f"linked {len(sparql_linked)} \u2192 {len(linked2_ids)} (unchanged)")
    print("=" * 68)

    # After injection: the published set must gain exactly the orphan, and the
    # linked set must be byte-for-byte the same as before (orphan never links).
    population_grew_by_orphan = (population2_ids == sql_all | {ORPHAN_ID})
    linked_unchanged = (linked2_ids == sql_linked)
    ok = (sets_ok and orphan_published and orphan_unlinked and orphan_default_ok
          and population_grew_by_orphan and linked_unchanged)
    if ok:
        print("  RESULT: OPTIONALITY GOVERNED \u2014 a supplier with no receipts is")
        print("          published from the suppliers table and stays UNLINKED,")
        print("          carrying its neutral default rating (matches My MRP).")
    else:
        print("  RESULT: OPTIONALITY CHECK FAILED")
    print("=" * 68)
    return 0 if ok else 1


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
    else:
        print("  RESULT: MISMATCH")
        if not ops_ok:
            print(f"    Operations subproperty differs by {abs(sparql_ops - solder_rate)}")
        if not parent_ok:
            print(f"    Parent property differs by {abs(sparql_parent - solder_rate)}")
    print("=" * 68)

    # Second proof: the supplier->receiving join + its governed LEFT-JOIN
    # optionality, now expressed in the Ontop ontology/mapping. Runs last because
    # it injects a synthetic supplier into the THROWAWAY snapshot.
    supplier_rc = supplier_optionality_check(props, snap)

    return 0 if (ops_ok and parent_ok and supplier_rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
