"""Tests for the operation schedule + cost-accrual migrations (Task #205).

These prove that the synthetic SQLite ``manufacturing.db`` reflects real ERP
job-costing after the two backfill migrations run:

  migrations/backfill_operation_schedule.py
    - every operation gets a non-NULL scheduled start/finish (both cohorts),
    - the routing chains: a step never starts before the prior step's scheduled
      finish OR its actual close_date,
    - the work-order window is read straight off the routing
      (work_order.sched_start_date = MIN op start, sched_finish_date = MAX op
      finish), and the planner release anchor (desired_rls_date) is always
      populated and lands on/before the first operation start.

  migrations/backfill_operation_actuals.py
    - internal labor/burden rollups are distributed DOWN to the progressed
      in-house operations so the operation actuals tie EXACTLY to the
      work_order.act_lab_cost / act_bur_cost rollups (residual on the last step),
    - a Queued in-house step accrues 0 internal labor/burden,
    - outside-service actuals (act_atl_ser_cost) are summed from the received
      outside-service POs by (wo_id, service_id) and tie to work_order.act_ser_cost.

The schedule columns themselves are proven two ways: present in the committed
schema DDL (fresh rebuild) and added in place by app.init_sqlite_db's self-heal
on an older database (existing-DB upgrade).

Run: python hf-space-inventory-sqlgen/tests/test_operation_schedule_cost_accrual.py
"""

from __future__ import annotations

import importlib
import os
import re
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)

SCHED_COLS = ("desired_rls_date", "sched_start_date", "sched_finish_date")


# ── helpers ──────────────────────────────────────────────────────────────────
def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _build_minimal_db(path):
    """Create the smallest schema the two migrations read/write, seeded with a
    representative scenario across BOTH work-order cohorts:

      WO-CLOSED-1 (closed cohort, has close_dates):
        seq 10  in-house  C  est 100/50  closes after its planned finish
        seq 20  in-house  C  est 200/100
        seq 30  in-house  S  est  80/40   (half recognized)
        seq 40  outside   Q  service 501, received PO of 300  (accrues despite Q)
      WO-OPEN-2 (24xx-style cohort):
        seq 10  in-house  C  est 500/250
        seq 20  in-house  Q  est 300/150  (queued -> 0 internal accrual)
    """
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE work_order (
            wo_id             TEXT PRIMARY KEY,
            open_date         DATETIME,
            close_date        DATETIME,
            status            TEXT,
            act_lab_cost      REAL,
            act_bur_cost      REAL,
            act_ser_cost      REAL,
            desired_rls_date  DATETIME,
            sched_start_date  DATETIME,
            sched_finish_date DATETIME
        );
        CREATE TABLE operation (
            rowid_pk          INTEGER PRIMARY KEY,
            wo_id             TEXT,
            sequence_no       INTEGER,
            service_id        INTEGER,
            setup_hrs         REAL,
            run_hrs           REAL,
            est_atl_lab_cost  REAL,
            est_atl_bur_cost  REAL,
            status            TEXT,
            close_date        DATETIME,
            sched_start_date  DATETIME,
            sched_finish_date DATETIME,
            act_atl_lab_cost  REAL DEFAULT 0.0,
            act_atl_bur_cost  REAL DEFAULT 0.0,
            act_atl_ser_cost  REAL DEFAULT 0.0
        );
        CREATE TABLE purchase_order (
            po_id       TEXT PRIMARY KEY,
            po_type     TEXT,
            wo_id       TEXT,
            service_id  INTEGER,
            total_cost  REAL
        );
        CREATE TABLE receiving (
            receiving_id INTEGER PRIMARY KEY,
            po_id        TEXT
        );
        """
    )
    # work_order rollups are the source of truth the actuals migration reconciles
    # to. They mirror how backfill_supplier_rating_and_wo_actuals builds them:
    #   act_lab = SUM(est_lab * STATUS_WEIGHT[status]) over progressed in-house ops
    #   WO-CLOSED-1: 100*1 + 200*1 + 80*0.5 = 340 ; bur: 50+100+20 = 170 ; ser=300
    #   WO-OPEN-2:   500*1                    = 500 ; bur: 250        ; ser=0
    conn.executemany(
        "INSERT INTO work_order (wo_id, open_date, close_date, status, "
        "act_lab_cost, act_bur_cost, act_ser_cost) VALUES (?,?,?,?,?,?,?)",
        [
            ("WO-CLOSED-1", "2025-01-06", "2025-01-20", "closed", 340.0, 170.0, 300.0),
            ("WO-OPEN-2", "2025-02-03", None, "released", 500.0, 250.0, 0.0),
        ],
    )
    conn.executemany(
        "INSERT INTO operation (rowid_pk, wo_id, sequence_no, service_id, "
        "setup_hrs, run_hrs, est_atl_lab_cost, est_atl_bur_cost, status, "
        "close_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            # WO-CLOSED-1 — close_date of seq 10 deliberately runs past its planned
            # 1-day finish so the schedule must stretch the finish to the close.
            (1, "WO-CLOSED-1", 10, None, 2.0, 6.0, 100.0, 50.0, "C", "2025-01-10"),
            (2, "WO-CLOSED-1", 20, None, 4.0, 12.0, 200.0, 100.0, "C", "2025-01-15"),
            (3, "WO-CLOSED-1", 30, None, 0.0, 0.0, 80.0, 40.0, "S", None),
            (4, "WO-CLOSED-1", 40, 501, 0.0, 0.0, 0.0, 0.0, "Q", None),
            # WO-OPEN-2
            (5, "WO-OPEN-2", 10, None, 8.0, 8.0, 500.0, 250.0, "C", "2025-02-10"),
            (6, "WO-OPEN-2", 20, None, 0.0, 0.0, 300.0, 150.0, "Q", None),
        ],
    )
    # One received outside-service PO tied to the outside op by (wo_id, service_id).
    conn.execute(
        "INSERT INTO purchase_order (po_id, po_type, wo_id, service_id, total_cost) "
        "VALUES (?,?,?,?,?)",
        ("PO-A", "outside_service", "WO-CLOSED-1", 501, 300.0),
    )
    conn.execute("INSERT INTO receiving (receiving_id, po_id) VALUES (1, 'PO-A')")
    conn.commit()
    conn.close()


def _run_migration(module_name, db_path):
    """Import a migration module, point its DB_PATH at ``db_path``, run it."""
    mod = importlib.import_module(module_name)
    mod = importlib.reload(mod)
    mod.DB_PATH = db_path
    mod.run()
    return mod


# ── schema / self-heal ───────────────────────────────────────────────────────
def test_schema_ddl_has_schedule_columns():
    """Fresh rebuild path: the committed work_order DDL carries all 3 columns."""
    schema_file = os.path.join(HF_DIR, "app_schema", "schema_sqlite.sql")
    with open(schema_file) as f:
        sql = f.read()
    m = re.search(r"CREATE TABLE IF NOT EXISTS work_order\s*\((.*?)\);", sql, re.S)
    assert m, "work_order CREATE TABLE not found in schema_sqlite.sql"
    block = m.group(1)
    for col in SCHED_COLS:
        assert re.search(rf"\b{col}\b", block), f"{col} missing from work_order DDL"
    print("PASS: schema_sqlite.sql work_order DDL carries all 3 schedule columns")


def test_init_self_heals_work_order_schedule_columns():
    """Existing-DB path: app.init_sqlite_db widens an older work_order in place."""
    try:
        import app as fastapi_app
    except Exception as exc:  # pragma: no cover - import guard
        print(f"SKIP: could not import app: {exc}")
        return

    # Build an authentic OLD-shape work_order: the committed CREATE block minus the
    # 3 new columns, so the only difference from current is the missing schedule.
    schema_file = os.path.join(HF_DIR, "app_schema", "schema_sqlite.sql")
    with open(schema_file) as f:
        sql = f.read()
    # Strip -- line comments before matching: a comment may contain ");" (e.g.
    # "-- ... (Release Order -> MO); NULL = unlinked MO"), which would otherwise
    # make the non-greedy regex terminate mid-statement -> "incomplete input".
    sql = re.sub(r"--[^\n]*", "", sql)
    m = re.search(r"(CREATE TABLE IF NOT EXISTS work_order\s*\(.*?\);)", sql, re.S)
    assert m, "work_order CREATE TABLE not found"
    stale_ddl = "\n".join(
        ln for ln in m.group(1).splitlines()
        if not any(c in ln for c in SCHED_COLS)
    )
    # Drop a dangling comma the removed trailing columns may have left behind.
    stale_ddl = re.sub(r",(\s*\);)", r"\1", stale_ddl)

    tmpdir = tempfile.mkdtemp(prefix="wo_self_heal_")
    stale_db = os.path.join(tmpdir, "manufacturing.db")
    conn = sqlite3.connect(stale_db)
    conn.executescript(stale_ddl)
    pre = _columns(conn, "work_order")
    conn.close()
    for col in SCHED_COLS:
        assert col not in pre, f"precondition: stale DB must lack {col}"

    orig_path = fastapi_app.SQLITE_DB_PATH
    orig_engine = fastapi_app.db_engine
    try:
        fastapi_app.SQLITE_DB_PATH = stale_db
        fastapi_app.db_engine = None
        fastapi_app.init_sqlite_db()
        conn = sqlite3.connect(stale_db)
        post = _columns(conn, "work_order")
        conn.close()
        for col in SCHED_COLS:
            assert col in post, f"self-heal did not add {col}. Columns: {sorted(post)}"
    finally:
        fastapi_app.SQLITE_DB_PATH = orig_path
        fastapi_app.db_engine = orig_engine
    print("PASS: init_sqlite_db self-heals work_order with the 3 schedule columns")


# ── schedule migration ───────────────────────────────────────────────────────
def test_no_null_operation_schedules_both_cohorts():
    tmpdir = tempfile.mkdtemp(prefix="sched_null_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_schedule", db)

    conn = sqlite3.connect(db)
    nulls = conn.execute(
        "SELECT COUNT(*) FROM operation "
        "WHERE sched_start_date IS NULL OR sched_finish_date IS NULL"
    ).fetchone()[0]
    # Both cohorts represented and scheduled.
    cohorts = conn.execute(
        "SELECT COUNT(DISTINCT wo_id) FROM operation WHERE sched_start_date IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert nulls == 0, f"{nulls} operations still have a NULL schedule"
    assert cohorts == 2, f"expected both cohorts scheduled, got {cohorts}"
    print("PASS: every operation in both cohorts has a non-NULL schedule")


def test_route_chain_invariant():
    """Each step's scheduled start is on/after the prior step's scheduled finish
    AND on/after the prior step's actual close_date."""
    tmpdir = tempfile.mkdtemp(prefix="sched_chain_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_schedule", db)

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT wo_id, sequence_no, sched_start_date, sched_finish_date, close_date "
        "FROM operation ORDER BY wo_id, sequence_no"
    ).fetchall()
    conn.close()

    by_wo = {}
    for wo_id, seq, ss, sf, cd in rows:
        by_wo.setdefault(wo_id, []).append((seq, ss, sf, cd))

    for wo_id, ops in by_wo.items():
        prev_finish = None
        prev_close = None
        for seq, ss, sf, cd in ops:
            assert ss <= sf, f"{wo_id} seq {seq}: start {ss} after finish {sf}"
            if prev_finish is not None:
                assert ss >= prev_finish, (
                    f"{wo_id} seq {seq}: start {ss} before prior finish {prev_finish}"
                )
            if prev_close is not None:
                assert ss >= prev_close, (
                    f"{wo_id} seq {seq}: start {ss} before prior close {prev_close}"
                )
            prev_finish = sf
            prev_close = cd or prev_close
    print("PASS: routing chain invariant holds (start >= prior finish and close)")


def test_completed_step_finish_stretches_to_close():
    """A completed step whose actual close ran past its planned finish has its
    scheduled finish stretched to the close (plan never finishes before reality)."""
    tmpdir = tempfile.mkdtemp(prefix="sched_stretch_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_schedule", db)

    conn = sqlite3.connect(db)
    # seq 10 of WO-CLOSED-1: open 2025-01-06, 1-day plan -> 2025-01-07, but it
    # closed 2025-01-10, so its scheduled finish must be >= the close.
    ss, sf, cd = conn.execute(
        "SELECT sched_start_date, sched_finish_date, close_date FROM operation "
        "WHERE wo_id='WO-CLOSED-1' AND sequence_no=10"
    ).fetchone()
    conn.close()
    assert sf >= cd, f"finish {sf} did not stretch to close {cd}"
    print("PASS: a completed step's scheduled finish stretches to its close_date")


def test_wo_window_equals_min_max_operation():
    tmpdir = tempfile.mkdtemp(prefix="sched_window_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_schedule", db)

    conn = sqlite3.connect(db)
    for wo_id, in (("WO-CLOSED-1",), ("WO-OPEN-2",)):
        ws, wf, wr, od = conn.execute(
            "SELECT sched_start_date, sched_finish_date, desired_rls_date, open_date "
            "FROM work_order WHERE wo_id=?", (wo_id,)
        ).fetchone()
        mn, mx = conn.execute(
            "SELECT MIN(sched_start_date), MAX(sched_finish_date) FROM operation "
            "WHERE wo_id=?", (wo_id,)
        ).fetchone()
        assert ws == mn, f"{wo_id}: WO start {ws} != min op start {mn}"
        assert wf == mx, f"{wo_id}: WO finish {wf} != max op finish {mx}"
        # desired_rls_date is always populated and lands on/before the first start.
        assert wr, f"{wo_id}: desired_rls_date not populated"
        assert wr <= ws, f"{wo_id}: desired_rls {wr} after sched_start {ws}"
        assert wr <= od, f"{wo_id}: desired_rls {wr} after open_date {od}"
    conn.close()
    print("PASS: WO window = MIN/MAX op; desired_rls_date populated and <= start")


def test_schedule_is_idempotent():
    tmpdir = tempfile.mkdtemp(prefix="sched_idem_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_schedule", db)
    conn = sqlite3.connect(db)
    first = conn.execute(
        "SELECT rowid_pk, sched_start_date, sched_finish_date FROM operation "
        "ORDER BY rowid_pk"
    ).fetchall()
    conn.close()
    _run_migration("migrations.backfill_operation_schedule", db)
    conn = sqlite3.connect(db)
    second = conn.execute(
        "SELECT rowid_pk, sched_start_date, sched_finish_date FROM operation "
        "ORDER BY rowid_pk"
    ).fetchall()
    conn.close()
    assert first == second, "schedule migration is not a fixed point (re-run differs)"
    print("PASS: schedule migration is idempotent (re-run reproduces identical state)")


# ── actuals migration ────────────────────────────────────────────────────────
def test_operation_actuals_tie_to_wo_rollups():
    tmpdir = tempfile.mkdtemp(prefix="actuals_tie_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_actuals", db)

    conn = sqlite3.connect(db)
    rows = conn.execute(
        """
        SELECT w.wo_id,
               ROUND(w.act_lab_cost, 2), ROUND(COALESCE(o.ol, 0), 2),
               ROUND(w.act_bur_cost, 2), ROUND(COALESCE(o.ob, 0), 2),
               ROUND(w.act_ser_cost, 2), ROUND(COALESCE(o.os, 0), 2)
        FROM work_order w
        LEFT JOIN (
            SELECT wo_id, SUM(act_atl_lab_cost) ol, SUM(act_atl_bur_cost) ob,
                   SUM(act_atl_ser_cost) os
            FROM operation GROUP BY wo_id
        ) o ON o.wo_id = w.wo_id
        """
    ).fetchall()
    conn.close()
    for wo_id, wl, ol, wb, ob, ws, os_ in rows:
        assert abs(wl - ol) < 0.01, f"{wo_id}: labor {ol} != rollup {wl}"
        assert abs(wb - ob) < 0.01, f"{wo_id}: burden {ob} != rollup {wb}"
        assert abs(ws - os_) < 0.01, f"{wo_id}: service {os_} != rollup {ws}"
    print("PASS: operation actuals reconcile EXACTLY to work_order rollups (lab/bur/ser)")


def test_queued_inhouse_step_accrues_zero_internal():
    tmpdir = tempfile.mkdtemp(prefix="actuals_q_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_actuals", db)
    conn = sqlite3.connect(db)
    # WO-OPEN-2 seq 20 is a Queued in-house step -> no recognized internal cost.
    lab, bur = conn.execute(
        "SELECT act_atl_lab_cost, act_atl_bur_cost FROM operation "
        "WHERE wo_id='WO-OPEN-2' AND sequence_no=20"
    ).fetchone()
    conn.close()
    assert lab == 0.0 and bur == 0.0, f"queued step accrued lab={lab} bur={bur}"
    print("PASS: a queued in-house step accrues 0 internal labor/burden")


def test_outside_service_actual_ties_to_received_po():
    tmpdir = tempfile.mkdtemp(prefix="actuals_ser_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_actuals", db)
    conn = sqlite3.connect(db)
    # The outside-service op (seq 40, service 501) accrues the received PO's cost
    # even though its status is still Queued (receipt is the accrual signal).
    ser = conn.execute(
        "SELECT act_atl_ser_cost FROM operation "
        "WHERE wo_id='WO-CLOSED-1' AND sequence_no=40"
    ).fetchone()[0]
    conn.close()
    assert abs(ser - 300.0) < 0.01, f"outside-service actual {ser} != received PO 300"
    print("PASS: outside-service actual equals the received outside-service PO total")


def test_actuals_is_idempotent():
    tmpdir = tempfile.mkdtemp(prefix="actuals_idem_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    _run_migration("migrations.backfill_operation_actuals", db)
    conn = sqlite3.connect(db)
    first = conn.execute(
        "SELECT rowid_pk, act_atl_lab_cost, act_atl_bur_cost, act_atl_ser_cost "
        "FROM operation ORDER BY rowid_pk"
    ).fetchall()
    conn.close()
    _run_migration("migrations.backfill_operation_actuals", db)
    conn = sqlite3.connect(db)
    second = conn.execute(
        "SELECT rowid_pk, act_atl_lab_cost, act_atl_bur_cost, act_atl_ser_cost "
        "FROM operation ORDER BY rowid_pk"
    ).fetchall()
    conn.close()
    assert first == second, "actuals migration is not a fixed point (re-run differs)"
    print("PASS: actuals migration is idempotent (re-run reproduces identical state)")


def main() -> int:
    tests = [
        test_schema_ddl_has_schedule_columns,
        test_init_self_heals_work_order_schedule_columns,
        test_no_null_operation_schedules_both_cohorts,
        test_route_chain_invariant,
        test_completed_step_finish_stretches_to_close,
        test_wo_window_equals_min_max_operation,
        test_schedule_is_idempotent,
        test_operation_actuals_tie_to_wo_rollups,
        test_queued_inhouse_step_accrues_zero_internal,
        test_outside_service_actual_ties_to_received_po,
        test_actuals_is_idempotent,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:  # pragma: no cover - surfaces unexpected errors
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
