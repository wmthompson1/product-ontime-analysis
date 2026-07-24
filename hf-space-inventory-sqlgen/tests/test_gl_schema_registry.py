"""Gate test — GL ledger semantic-layer registration + reconciliation.

Locks the invariants of migrations/add_gl_schema_registry.py:
  - all five gl_* tables registered in schema_nodes;
  - schema_edges join-graph rows (32-43) present for every declared FK;
  - declared FKs visible via PRAGMA foreign_key_list (structural layer);
  - every ledger line resolves to a real gl_events parent with the same
    event_date;
  - RM outflow reconciles cent-exact to material_issue.total_cost;
  - WIP labor / burden reconcile as-is to labor_ticket (never recomputed);
  - WIP nets to zero for closed jobs; FG inflow == WIP completion outflow;
  - no planned orders (WO-PLN-*) anywhere in the ledger;
  - gl_job_cost_detail ties per job to work_order.act_mat/lab/bur_cost;
  - graph coverage: committed graph_metadata.json carries the gl_* table
    and column nodes (SCHEMA_VERSION >= 29).

Run gate-style:
    cd hf-space-inventory-sqlgen
    python tests/test_gl_schema_registry.py
"""

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
GRAPH_JSON = os.path.join(
    os.path.dirname(HF_DIR), "replit_integrations", "graph_metadata.json"
)

GL_TABLES = [
    "gl_events",
    "gl_raw_materials_inventory",
    "gl_wip_inventory",
    "gl_finished_goods_inventory",
    "gl_job_cost_detail",
]
LINE_TABLES = GL_TABLES[1:]
CENT = 0.005

FAILURES = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1 — registry
    reg = {
        r[0] for r in cur.execute(
            "SELECT table_name FROM schema_nodes WHERE table_name LIKE 'gl_%'"
        )
    }
    check("schema_nodes registers all five gl_* tables",
          reg == set(GL_TABLES), str(sorted(reg)))

    # 2 — join graph
    want_edges = {
        ("gl_events", "work_order", "job_id"),
        ("gl_raw_materials_inventory", "gl_events", "event_id"),
        ("gl_raw_materials_inventory", "work_order", "job_id"),
        ("gl_raw_materials_inventory", "part", "part_id"),
        ("gl_wip_inventory", "gl_events", "event_id"),
        ("gl_wip_inventory", "work_order", "job_id"),
        ("gl_wip_inventory", "part", "part_id"),
        ("gl_finished_goods_inventory", "gl_events", "event_id"),
        ("gl_finished_goods_inventory", "work_order", "job_id"),
        ("gl_finished_goods_inventory", "part", "part_id"),
        ("gl_job_cost_detail", "gl_events", "event_id"),
        ("gl_job_cost_detail", "work_order", "job_id"),
    }
    got_edges = {
        (r[0], r[1], r[2]) for r in cur.execute(
            "SELECT from_table, to_table, join_column FROM schema_edges "
            "WHERE from_table LIKE 'gl_%'"
        )
    }
    check("schema_edges join-graph rows exact", got_edges == want_edges,
          f"got {sorted(got_edges)}")

    # 3 — declared FKs (structural layer the exporter mints references from)
    for t in GL_TABLES:
        # PRAGMA columns: (id, seq, parent_table, child_col, parent_col, ...)
        fks = {(f[2], f[3], f[4]) for f in cur.execute(f"PRAGMA foreign_key_list({t})")}
        check(f"{t} declares FK job_id -> work_order.wo_id",
              ("work_order", "job_id", "wo_id") in fks, str(fks))

    # 4 — ledger lines hang off real events, same date
    for t in LINE_TABLES:
        dangling = cur.execute(
            f"SELECT COUNT(*) FROM {t} l LEFT JOIN gl_events e "
            "ON e.event_id = l.event_id WHERE e.event_id IS NULL"
        ).fetchone()[0]
        check(f"{t}: no dangling event_id", dangling == 0, str(dangling))
        redated = cur.execute(
            f"SELECT COUNT(*) FROM {t} l JOIN gl_events e "
            "ON e.event_id = l.event_id WHERE l.event_date != e.event_date"
        ).fetchone()[0]
        check(f"{t}: line dates match their events", redated == 0, str(redated))

    # 5 — cent-exact source reconciliation
    rm_out = cur.execute(
        "SELECT COALESCE(ROUND(-SUM(amount),2),0) "
        "FROM gl_raw_materials_inventory WHERE amount < 0"
    ).fetchone()[0]
    mi_total = cur.execute(
        "SELECT COALESCE(ROUND(SUM(total_cost),2),0) FROM material_issue"
    ).fetchone()[0]
    check("RM outflow == material_issue total (cent-exact)",
          abs(rm_out - mi_total) <= CENT, f"{rm_out} vs {mi_total}")

    for ev_type, src_col in [("LABOR", "labor_cost"), ("BURDEN", "burden_cost")]:
        wip = cur.execute(
            "SELECT COALESCE(ROUND(SUM(amount),2),0) FROM gl_wip_inventory "
            "WHERE event_type = ?", (ev_type,)
        ).fetchone()[0]
        src = cur.execute(
            f"SELECT COALESCE(ROUND(SUM({src_col}),2),0) FROM labor_ticket"
        ).fetchone()[0]
        check(f"WIP {ev_type} == labor_ticket {src_col} (as-is)",
              abs(wip - src) <= CENT, f"{wip} vs {src}")

    # 6 — WIP zero for closed jobs; FG == WIP completion outflow
    bad_wip = cur.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT w.job_id FROM gl_wip_inventory w
          JOIN work_order wo ON wo.wo_id = w.job_id
          WHERE wo.status = 'closed'
          GROUP BY w.job_id HAVING ABS(SUM(w.amount)) > 0.005)
        """
    ).fetchone()[0]
    check("WIP nets to zero for closed jobs", bad_wip == 0, str(bad_wip))

    fg_drift = cur.execute(
        """
        SELECT COUNT(*) FROM
          (SELECT job_id, ROUND(SUM(amount),2) fg
           FROM gl_finished_goods_inventory
           WHERE event_type = 'FG_COMPLETION' GROUP BY job_id) f
        LEFT JOIN
          (SELECT job_id, ROUND(-SUM(amount),2) wip_out FROM gl_wip_inventory
           WHERE amount < 0 GROUP BY job_id) w ON w.job_id = f.job_id
        WHERE w.job_id IS NULL OR ABS(f.fg - w.wip_out) > 0.005
        """
    ).fetchone()[0]
    check("FG inflow == WIP completion outflow per job", fg_drift == 0, str(fg_drift))

    # 7 — no planned orders in the ledger
    pln = 0
    for t in GL_TABLES:
        pln += cur.execute(
            f"SELECT COUNT(*) FROM {t} WHERE job_id LIKE 'WO-PLN-%'"
        ).fetchone()[0]
    check("no WO-PLN-* rows anywhere in the ledger", pln == 0, str(pln))

    # 8 — job cost detail ties to work_order cost truth
    bad_jobs = cur.execute(
        """
        SELECT COUNT(*) FROM
          (SELECT job_id,
                  ROUND(SUM(CASE WHEN event_type='MATERIAL' THEN amount END),2) m,
                  ROUND(SUM(CASE WHEN event_type='LABOR'    THEN amount END),2) l,
                  ROUND(SUM(CASE WHEN event_type='BURDEN'   THEN amount END),2) b
           FROM gl_job_cost_detail GROUP BY job_id) d
        JOIN work_order wo ON wo.wo_id = d.job_id
        WHERE ABS(COALESCE(d.m,0) - wo.act_mat_cost) > 0.005
           OR ABS(COALESCE(d.l,0) - wo.act_lab_cost) > 0.005
           OR ABS(COALESCE(d.b,0) - wo.act_bur_cost) > 0.005
        """
    ).fetchone()[0]
    check("gl_job_cost_detail ties to work_order actuals per job",
          bad_jobs == 0, str(bad_jobs))

    conn.close()

    # 9 — fail-closed atomicity: on reconciliation drift, the migration must
    # roll back and leave NO gl_* registry rows behind (temp DB copy).
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = os.path.join(tmpdir, "drift.db")
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(tmp_db)
        src.backup(dst)
        src.close()
        c = dst.cursor()
        c.execute("DELETE FROM schema_nodes WHERE table_name LIKE 'gl_%'")
        c.execute("DELETE FROM schema_edges WHERE from_table LIKE 'gl_%'")
        c.execute(
            "UPDATE gl_wip_inventory SET amount = amount + 100.0 "
            "WHERE line_id = (SELECT MIN(line_id) FROM gl_wip_inventory)"
        )
        dst.commit()
        dst.close()
        proc = subprocess.run(
            [sys.executable,
             os.path.join(HF_DIR, "migrations", "add_gl_schema_registry.py"),
             "--db", tmp_db],
            capture_output=True, text=True,
        )
        check("drifted ledger makes the migration fail closed",
              proc.returncode != 0, proc.stdout + proc.stderr)
        chk = sqlite3.connect(tmp_db)
        leftover = chk.execute(
            "SELECT (SELECT COUNT(*) FROM schema_nodes WHERE table_name LIKE 'gl_%') + "
            "(SELECT COUNT(*) FROM schema_edges WHERE from_table LIKE 'gl_%')"
        ).fetchone()[0]
        chk.close()
        check("failed migration leaves no gl_* registry rows (rolled back)",
              leftover == 0, str(leftover))

    # 10 — committed graph carries the gl_* nodes
    with open(GRAPH_JSON, encoding="utf-8") as fh:
        doc = json.load(fh)
    check("graph SCHEMA_VERSION >= 29", doc.get("schema_version", 0) >= 29,
          str(doc.get("schema_version")))
    table_nodes = {
        n.get("table_name") for n in doc.get("nodes", [])
        if n.get("node_type") == "table"
    }
    check("graph has all five gl_* table nodes",
          set(GL_TABLES) <= table_nodes,
          str(sorted(set(GL_TABLES) - table_nodes)))
    gl_cols = [
        n for n in doc.get("nodes", [])
        if n.get("node_type") == "column" and n.get("table_name") in GL_TABLES
    ]
    check("graph has the 34 gl_* column nodes", len(gl_cols) == 34, str(len(gl_cols)))

    # 11 — CASH_RECEIPT amounts are all positive (cash inflows)
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    negative_cr = cur2.execute(
        "SELECT COUNT(*) FROM gl_events WHERE event_type = 'CASH_RECEIPT' AND amount <= 0"
    ).fetchone()[0]
    check("all CASH_RECEIPT amounts are positive", negative_cr == 0, str(negative_cr))
    conn2.close()

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
