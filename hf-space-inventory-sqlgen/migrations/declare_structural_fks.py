"""
migrations/declare_structural_fks.py
------------------------------------
Re-declare the structural foreign keys the frozen graph records but a
fresh-bootstrap database's DDL lacks.

Background: the canonical graph (replit_integrations/graph_metadata.json) was
exported FROM PRAGMA foreign_key_list of the evolved live database, whose ERP
tables had been rebuilt with declared FKs. schema_sqlite.sql and the migration
chain create several of those tables with comment-only FKs, so a fresh
bootstrap loses the declarations — and PRAGMA-driven consumers (metric
assembly's declared-FK-only join resolver) then fail closed.

FK enforcement is OFF in this project (house style: declared FKs are
structural-only metadata, declared even over orphan rows), so declarations are
inert at runtime. That lets this migration append the missing FOREIGN KEY
clauses in place via writable_schema instead of a copy-rebuild — no data is
touched, and indexes/triggers on the tables are preserved.

Source of truth: the committed graph JSON's `references` edges (child column ->
parent table/column). BOTH origins are declared intentionally: `fk_declared`
edges mirror the old DDL, and `sql_observed` edges (e.g. purchase_order.po_id
-> receiving.po_id) are required by the declared-FK-only metric join resolver
— the references layer as a whole is the structural ground truth, regardless
of how each edge was first captured. Tuples are deduped before rewrite (the
JSON carries fk_declared/sql_observed twins for a few pairs), so each FK is
declared exactly once. Idempotent: FKs already declared are skipped;
re-running adds nothing.

Usage:
    python migrations/declare_structural_fks.py [--db PATH] [--json PATH]
"""

import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)

DEFAULT_DB = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
DEFAULT_JSON = os.path.join(REPO_ROOT, "replit_integrations", "graph_metadata.json")


def graph_reference_fks(json_path):
    """[(child_table, child_col, parent_table, parent_col)] from references edges."""
    with open(json_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    fks = []
    for e in doc.get("edges", []):
        if e.get("edge_type") != "references":
            continue
        # _from: "<collection>/<child_table>:<child_col>:<family>:..."
        key = e["_from"].split("/", 1)[-1]
        parts = key.split(":")
        if len(parts) < 2:
            raise SystemExit(f"FAIL-CLOSED: unparseable references edge _from: {e['_from']}")
        child_table, child_col = parts[0], parts[1]
        parent_table = e.get("references_table")
        parent_col = e.get("references_column")
        if not parent_table or not parent_col:
            raise SystemExit(
                f"FAIL-CLOSED: references edge missing references_table/column: {e.get('_key')}"
            )
        tup = (child_table, child_col, parent_table, parent_col)
        if tup not in fks:
            fks.append(tup)
    if not fks:
        raise SystemExit("FAIL-CLOSED: no references edges found in graph JSON")
    return fks


def declared_fks(conn, table):
    return {
        (table, r["from"], r["table"], r["to"])
        for r in conn.execute(f'PRAGMA foreign_key_list("{table}")')
    }


def table_columns(conn, table):
    return {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", default=DEFAULT_JSON)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"FAIL-CLOSED: database not found: {args.db}")
    if not os.path.exists(args.json):
        raise SystemExit(f"FAIL-CLOSED: graph JSON not found: {args.json}")

    wanted = graph_reference_fks(args.json)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}

        # Group the missing declarations per child table.
        missing_by_table = {}
        for child, col, parent, pcol in wanted:
            if child not in tables:
                raise SystemExit(
                    f"FAIL-CLOSED: graph declares FK on missing table '{child}'")
            if parent not in tables:
                raise SystemExit(
                    f"FAIL-CLOSED: graph FK references missing parent table '{parent}'")
            if col not in table_columns(conn, child):
                raise SystemExit(
                    f"FAIL-CLOSED: graph FK on missing column {child}.{col}")
            if (child, col, parent, pcol) in declared_fks(conn, child):
                continue
            missing_by_table.setdefault(child, []).append((col, parent, pcol))

        if not missing_by_table:
            print("declare_structural_fks: all graph FKs already declared — nothing to do")
            return

        cur = conn.cursor()
        cur.execute("PRAGMA writable_schema=ON")
        for child, fks in sorted(missing_by_table.items()):
            row = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (child,),
            ).fetchone()
            ddl = row["sql"]
            close_at = ddl.rstrip().rfind(")")
            if close_at == -1:
                raise SystemExit(f"FAIL-CLOSED: cannot parse DDL for '{child}'")
            clauses = ",\n".join(
                f'    FOREIGN KEY ("{col}") REFERENCES "{parent}"("{pcol}")'
                for col, parent, pcol in fks
            )
            new_ddl = ddl[:close_at].rstrip() + ",\n" + clauses + "\n" + ddl[close_at:]
            cur.execute(
                "UPDATE sqlite_master SET sql=? WHERE type='table' AND name=?",
                (new_ddl, child),
            )
            for col, parent, pcol in fks:
                print(f"  declared: {child}.{col} -> {parent}.{pcol}")
        # Bump the schema cookie so other connections reload the new DDL.
        ver = cur.execute("PRAGMA schema_version").fetchone()[0]
        cur.execute(f"PRAGMA schema_version={ver + 1}")
        cur.execute("PRAGMA writable_schema=OFF")
        conn.commit()
    finally:
        conn.close()

    # Fresh connection: verify the rewritten DDL parses and every wanted FK is
    # now visible to PRAGMA foreign_key_list. Fail closed otherwise.
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise SystemExit(f"FAIL-CLOSED: integrity_check after rewrite: {ok}")
        still_missing = [
            fk for fk in wanted
            if fk not in declared_fks(conn, fk[0])
        ]
        if still_missing:
            raise SystemExit(
                f"FAIL-CLOSED: {len(still_missing)} FK(s) still undeclared "
                f"after rewrite, e.g. {still_missing[:3]}"
            )
        total = sum(len(declared_fks(conn, t)) for t in
                    {fk[0] for fk in wanted})
        print(f"declare_structural_fks: OK — all {len(wanted)} graph FKs declared "
              f"({total} declarations on the touched tables); integrity ok")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
