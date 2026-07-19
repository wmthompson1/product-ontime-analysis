"""
migrations/add_gl_ledger_tables.py
----------------------------------
Create the minimal synthetic GL ledger tables (DDL only — no data, no
control logic, no reconciliation machinery).

Tables (shared minimal shape — id, job_id, amount, event_date, event_type,
plus part/source linkage where it costs nothing):

  gl_raw_materials_inventory   RM inventory ledger lines
  gl_wip_inventory             WIP inventory ledger lines
  gl_finished_goods_inventory  FG inventory ledger lines
  gl_job_cost_detail           per-job cost detail lines
  gl_events                    the event log the ledger lines hang off

Design rules:
  * job_id is the existing work_order.wo_id. The FOREIGN KEY clauses are
    structural-only (FK enforcement is OFF in this project) — declared for
    graph derivation, inert at runtime.
  * event_date carries NO default: every timestamp must be data-derived
    from a source document (material_issue.issue_date, labor_ticket
    clock times, operation.close_date, receiving.receipt_date, ...),
    never wall-clock. Population is a later task's job.
  * Deliberately minimal: no period-close, control-account, or validation
    columns.

Idempotent: CREATE TABLE IF NOT EXISTS — safe to re-run.

Usage:
    python migrations/add_gl_ledger_tables.py [--db PATH]
"""

import argparse
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
DEFAULT_DB = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

GL_TABLES = [
    "gl_raw_materials_inventory",
    "gl_wip_inventory",
    "gl_finished_goods_inventory",
    "gl_job_cost_detail",
    "gl_events",
]

DDL = """
-- Event log: one row per economic event the ledger lines reference.
CREATE TABLE IF NOT EXISTS gl_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT,                   -- FK -> work_order.wo_id (structural)
    event_type  TEXT NOT NULL,          -- e.g. RM_ISSUE / LABOR / BURDEN / SERVICE / FG_COMPLETION
    amount      REAL NOT NULL DEFAULT 0.0,
    event_date  DATETIME NOT NULL,      -- data-derived from the source document, never wall-clock
    source_table TEXT,                  -- originating document table (material_issue, labor_ticket, ...)
    source_id   TEXT,                   -- originating document row key
    FOREIGN KEY (job_id) REFERENCES work_order (wo_id)
);

-- Raw-materials inventory ledger lines.
CREATE TABLE IF NOT EXISTS gl_raw_materials_inventory (
    line_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER,                -- FK -> gl_events (structural)
    job_id      TEXT,                   -- FK -> work_order.wo_id (structural)
    part_id     TEXT,                   -- FK -> part (structural)
    amount      REAL NOT NULL DEFAULT 0.0,   -- signed: + into RM, - out of RM
    event_type  TEXT NOT NULL,
    event_date  DATETIME NOT NULL,      -- data-derived, never wall-clock
    FOREIGN KEY (event_id) REFERENCES gl_events (event_id),
    FOREIGN KEY (job_id) REFERENCES work_order (wo_id),
    FOREIGN KEY (part_id) REFERENCES part (part_id)
);

-- Work-in-process inventory ledger lines.
CREATE TABLE IF NOT EXISTS gl_wip_inventory (
    line_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER,                -- FK -> gl_events (structural)
    job_id      TEXT,                   -- FK -> work_order.wo_id (structural)
    part_id     TEXT,                   -- FK -> part (structural)
    amount      REAL NOT NULL DEFAULT 0.0,   -- signed: + into WIP, - out of WIP
    event_type  TEXT NOT NULL,
    event_date  DATETIME NOT NULL,      -- data-derived, never wall-clock
    FOREIGN KEY (event_id) REFERENCES gl_events (event_id),
    FOREIGN KEY (job_id) REFERENCES work_order (wo_id),
    FOREIGN KEY (part_id) REFERENCES part (part_id)
);

-- Finished-goods inventory ledger lines.
CREATE TABLE IF NOT EXISTS gl_finished_goods_inventory (
    line_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER,                -- FK -> gl_events (structural)
    job_id      TEXT,                   -- FK -> work_order.wo_id (structural)
    part_id     TEXT,                   -- FK -> part (structural)
    amount      REAL NOT NULL DEFAULT 0.0,   -- signed: + into FG, - out of FG
    event_type  TEXT NOT NULL,
    event_date  DATETIME NOT NULL,      -- data-derived, never wall-clock
    FOREIGN KEY (event_id) REFERENCES gl_events (event_id),
    FOREIGN KEY (job_id) REFERENCES work_order (wo_id),
    FOREIGN KEY (part_id) REFERENCES part (part_id)
);

-- Per-job cost detail lines (labor / material / burden / service by job).
CREATE TABLE IF NOT EXISTS gl_job_cost_detail (
    line_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER,                -- FK -> gl_events (structural)
    job_id      TEXT NOT NULL,          -- FK -> work_order.wo_id (structural)
    amount      REAL NOT NULL DEFAULT 0.0,
    event_type  TEXT NOT NULL,          -- cost element: LABOR / MATERIAL / BURDEN / SERVICE
    event_date  DATETIME NOT NULL,      -- data-derived, never wall-clock
    FOREIGN KEY (event_id) REFERENCES gl_events (event_id),
    FOREIGN KEY (job_id) REFERENCES work_order (wo_id)
);
"""


def run(db_path: str = DEFAULT_DB) -> None:
    if not os.path.exists(db_path):
        raise SystemExit(f"FAIL-CLOSED: database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DDL)
        conn.commit()
        # Self-check: all five tables must exist.
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gl_%'"
        ).fetchall()
        found = {r[0] for r in rows}
        missing = [t for t in GL_TABLES if t not in found]
        if missing:
            raise SystemExit(f"FAIL-CLOSED: GL tables missing after DDL: {missing}")
        for t in GL_TABLES:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: OK ({n} rows)")
        print("[gl-ledger] all 5 GL tables present — re-run is a no-op.")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()
    run(args.db)
