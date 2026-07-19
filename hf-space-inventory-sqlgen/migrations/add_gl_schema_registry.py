"""Register the GL ledger tables in the semantic-layer schema registry.

The minimal synthetic GL ledger (migrations/add_gl_ledger_tables.py) and its
deterministic backfill (migrations/backfill_gl_ledger.py) created and
populated five tables:

    gl_events                    economic-event log (idempotency spine)
    gl_raw_materials_inventory   RM ledger lines  (signed: + in, - out)
    gl_wip_inventory             WIP ledger lines (signed: + in, - out)
    gl_finished_goods_inventory  FG ledger lines  (signed: + in, - out)
    gl_job_cost_detail           per-job cost-element detail

but never registered them in the semantic layer, so the Schema Browser, the
graph exporter (which enumerates schema_nodes), and the join-graph
(schema_edges) cannot see them.  This migration mirrors the receivables
precedent (migrations/add_receivable_tables.py, Phase 2):

1. REGISTRY  — schema_nodes rows for all five tables.
2. JOIN GRAPH — schema_edges rows (edge_ids 32-43) for every declared FK:
       gl_events                   -> work_order (job_id)
       gl_raw_materials_inventory  -> gl_events / work_order / part
       gl_wip_inventory            -> gl_events / work_order / part
       gl_finished_goods_inventory -> gl_events / work_order / part
       gl_job_cost_detail          -> gl_events / work_order
3. RECONCILIATION VERIFY (fail-closed) — proves the ledger the registry now
   exposes is internally sound and tied to its sources to the cent:
       - registry + join-graph rows present exactly as declared;
       - every ledger line's event_id resolves to a real gl_events row and
         carries the same event_date (no dangling / re-dated lines);
       - RM outflow == material_issue total_cost (cent-exact);
       - WIP labor == labor_ticket labor_cost, WIP burden == burden_cost;
       - WIP nets to zero for every closed job; no WO-PLN-* job anywhere;
       - FG inflow == WIP completion outflow per job (cent-exact);
       - gl_job_cost_detail per job ties to work_order.act_mat/lab/bur_cost.

Idempotent (INSERT OR IGNORE + read-only verify) — safe to re-run.

Usage:
    cd hf-space-inventory-sqlgen
    python migrations/add_gl_schema_registry.py [--db PATH]
"""

import argparse
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
DEFAULT_DB = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

CENT = 0.005  # cent-exact tolerance

REGISTRY = [
    ("gl_events",
     "GL economic-event log — one row per posted costing event (material issue, labor, burden, job completion) with source-document provenance"),
    ("gl_raw_materials_inventory",
     "Raw-materials inventory ledger lines — signed dollar movements into (+) and out of (-) the RM account, hung off gl_events"),
    ("gl_wip_inventory",
     "Work-in-process inventory ledger lines — signed dollar movements into (+) and out of (-) the WIP account, hung off gl_events"),
    ("gl_finished_goods_inventory",
     "Finished-goods inventory ledger lines — signed dollar movements into (+) and out of (-) the FG account, hung off gl_events"),
    ("gl_job_cost_detail",
     "Per-job cost-element detail lines (material / labor / burden) tying each posted dollar back to its work order"),
]

# schema_edges join-graph rows; ids continue after the receivables block (29-31).
EDGES = [
    (32, "gl_events",                   "work_order", "FOREIGN_KEY", "job_id",
     "GL event posted against a work order (job)"),
    (33, "gl_raw_materials_inventory",  "gl_events",  "FOREIGN_KEY", "event_id",
     "RM ledger line hangs off a GL event"),
    (34, "gl_raw_materials_inventory",  "work_order", "FOREIGN_KEY", "job_id",
     "RM ledger line charged to a work order"),
    (35, "gl_raw_materials_inventory",  "part",       "FOREIGN_KEY", "part_id",
     "RM ledger line moves a part's material dollars"),
    (36, "gl_wip_inventory",            "gl_events",  "FOREIGN_KEY", "event_id",
     "WIP ledger line hangs off a GL event"),
    (37, "gl_wip_inventory",            "work_order", "FOREIGN_KEY", "job_id",
     "WIP ledger line accumulates cost on a work order"),
    (38, "gl_wip_inventory",            "part",       "FOREIGN_KEY", "part_id",
     "WIP ledger line tied to the part being built"),
    (39, "gl_finished_goods_inventory", "gl_events",  "FOREIGN_KEY", "event_id",
     "FG ledger line hangs off a GL event"),
    (40, "gl_finished_goods_inventory", "work_order", "FOREIGN_KEY", "job_id",
     "FG ledger line receives a completed work order's cost"),
    (41, "gl_finished_goods_inventory", "part",       "FOREIGN_KEY", "part_id",
     "FG ledger line stocks the finished part"),
    (42, "gl_job_cost_detail",          "gl_events",  "FOREIGN_KEY", "event_id",
     "Job cost detail line hangs off a GL event"),
    (43, "gl_job_cost_detail",          "work_order", "FOREIGN_KEY", "job_id",
     "Job cost detail line belongs to a work order"),
]

GL_TABLES = [t for t, _ in REGISTRY]
LINE_TABLES = [
    "gl_raw_materials_inventory",
    "gl_wip_inventory",
    "gl_finished_goods_inventory",
    "gl_job_cost_detail",
]


def fail(msg):
    raise SystemExit(f"[add_gl_schema_registry] FAIL-CLOSED: {msg}")


def run(db_path=DEFAULT_DB):
    print(f"DB path: {os.path.abspath(db_path)}")
    if not os.path.exists(db_path):
        fail(f"database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    try:
        _run_phases(conn, cur)
    except BaseException:
        conn.rollback()
        conn.close()
        raise
    conn.commit()
    conn.close()
    print("Done.")


def _run_phases(conn, cur):

    have = {
        r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gl_%'"
        )
    }
    missing = [t for t in GL_TABLES if t not in have]
    if missing:
        fail(f"GL tables missing (run add_gl_ledger_tables.py first): {missing}")

    # Phase 1 — registry + join graph
    print("Phase 1 — register in schema_nodes / schema_edges ...")
    for table_name, description in REGISTRY:
        cur.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
    for edge_id, ft, tt, rel, col, alias in EDGES:
        cur.execute(
            "INSERT OR IGNORE INTO schema_edges "
            "(edge_id, from_table, to_table, relationship_type, join_column, weight, natural_language_alias) "
            "VALUES (?,?,?,?,?,1,?)",
            (edge_id, ft, tt, rel, col, alias),
        )
    # NOTE: no commit yet — registration only becomes durable after every
    # verification and reconciliation check below passes (atomic fail-closed).

    # Phase 2 — fail-closed verify (registry)
    print("Phase 2 — verify registry + join graph ...")
    reg = {
        r[0] for r in cur.execute(
            "SELECT table_name FROM schema_nodes WHERE table_name LIKE 'gl_%'"
        )
    }
    if reg != set(GL_TABLES):
        fail(f"schema_nodes registry drift: got {sorted(reg)}")
    got_edges = {
        (r[0], r[1], r[2]) for r in cur.execute(
            "SELECT from_table, to_table, join_column FROM schema_edges "
            "WHERE from_table LIKE 'gl_%'"
        )
    }
    want_edges = {(ft, tt, col) for _e, ft, tt, _r, col, _a in EDGES}
    if got_edges != want_edges:
        fail(
            "schema_edges join-graph rows missing or drifted (edge-id collision?): "
            f"got {sorted(got_edges)}, want {sorted(want_edges)}"
        )

    # Phase 3 — fail-closed reconciliation of the ledger the registry exposes
    print("Phase 3 — reconcile ledger to source documents (cent-exact) ...")

    # 3a. every ledger line resolves to a real event with the same date
    for t in LINE_TABLES:
        dangling = cur.execute(
            f"SELECT COUNT(*) FROM {t} l LEFT JOIN gl_events e "
            "ON e.event_id = l.event_id WHERE e.event_id IS NULL"
        ).fetchone()[0]
        if dangling:
            fail(f"{t}: {dangling} line(s) with no gl_events parent")
        redated = cur.execute(
            f"SELECT COUNT(*) FROM {t} l JOIN gl_events e "
            "ON e.event_id = l.event_id WHERE l.event_date != e.event_date"
        ).fetchone()[0]
        if redated:
            fail(f"{t}: {redated} line(s) whose event_date drifts from their event")

    # 3b. RM outflow == material_issue total_cost
    rm_out = cur.execute(
        "SELECT COALESCE(ROUND(-SUM(amount),2),0) FROM gl_raw_materials_inventory "
        "WHERE amount < 0"
    ).fetchone()[0]
    mi_total = cur.execute(
        "SELECT COALESCE(ROUND(SUM(total_cost),2),0) FROM material_issue"
    ).fetchone()[0]
    if abs(rm_out - mi_total) > CENT:
        fail(f"RM outflow {rm_out} != material_issue total {mi_total}")

    # 3c. WIP labor / burden tie to labor_ticket as-is (never recomputed)
    for ev_type, src_col in [("LABOR", "labor_cost"), ("BURDEN", "burden_cost")]:
        wip = cur.execute(
            "SELECT COALESCE(ROUND(SUM(amount),2),0) FROM gl_wip_inventory "
            "WHERE event_type = ?", (ev_type,)
        ).fetchone()[0]
        src = cur.execute(
            f"SELECT COALESCE(ROUND(SUM({src_col}),2),0) FROM labor_ticket"
        ).fetchone()[0]
        if abs(wip - src) > CENT:
            fail(f"WIP {ev_type} {wip} != labor_ticket {src_col} {src}")

    # 3d. no planned orders anywhere in the ledger
    for t in ["gl_events"] + LINE_TABLES:
        pln = cur.execute(
            f"SELECT COUNT(*) FROM {t} WHERE job_id LIKE 'WO-PLN-%'"
        ).fetchone()[0]
        if pln:
            fail(f"{t}: {pln} row(s) posted against planned orders (WO-PLN-*)")

    # 3e. WIP nets to zero for every closed job; FG inflow == WIP completion out
    bad_wip = cur.execute(
        """
        SELECT w.job_id, ROUND(SUM(w.amount),2) FROM gl_wip_inventory w
        JOIN work_order wo ON wo.wo_id = w.job_id
        WHERE wo.status = 'closed'
        GROUP BY w.job_id HAVING ABS(SUM(w.amount)) > ?
        """, (CENT,)
    ).fetchall()
    if bad_wip:
        fail(f"WIP does not net to zero for closed job(s): {bad_wip}")
    drift = cur.execute(
        """
        SELECT COUNT(*) FROM
          (SELECT job_id, ROUND(SUM(amount),2) fg FROM gl_finished_goods_inventory
           GROUP BY job_id) f
        LEFT JOIN
          (SELECT job_id, ROUND(-SUM(amount),2) wip_out FROM gl_wip_inventory
           WHERE amount < 0 GROUP BY job_id) w
          ON w.job_id = f.job_id
        WHERE w.job_id IS NULL OR ABS(f.fg - w.wip_out) > ?
        """, (CENT,)
    ).fetchone()[0]
    if drift:
        fail(f"{drift} job(s) where FG inflow != WIP completion outflow")

    # 3f. job cost detail ties to the work_order cost truth per job
    bad_jobs = cur.execute(
        """
        SELECT d.job_id FROM
          (SELECT job_id,
                  ROUND(SUM(CASE WHEN event_type='MATERIAL' THEN amount END),2) m,
                  ROUND(SUM(CASE WHEN event_type='LABOR'    THEN amount END),2) l,
                  ROUND(SUM(CASE WHEN event_type='BURDEN'   THEN amount END),2) b
           FROM gl_job_cost_detail GROUP BY job_id) d
        JOIN work_order wo ON wo.wo_id = d.job_id
        WHERE ABS(COALESCE(d.m,0) - wo.act_mat_cost) > ?
           OR ABS(COALESCE(d.l,0) - wo.act_lab_cost) > ?
           OR ABS(COALESCE(d.b,0) - wo.act_bur_cost) > ?
        """, (CENT, CENT, CENT)
    ).fetchall()
    if bad_jobs:
        fail(f"gl_job_cost_detail does not tie to work_order costs for: {bad_jobs}")

    n_ev = cur.execute("SELECT COUNT(*) FROM gl_events").fetchone()[0]
    print(f"All reconciliation checks passed ({n_ev} events; "
          f"RM out {rm_out}, ties to material_issue {mi_total}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()
    run(args.db)
