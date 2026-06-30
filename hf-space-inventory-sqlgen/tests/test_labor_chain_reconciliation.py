"""Tests for the bottom-up labor-chain rebuild (migrations/backfill_labor_chain.py).

These prove the synthetic SQLite ``manufacturing.db`` reflects a coherent labor
chain where all three layers agree and burden is rate-consistent:

  labor_ticket  ->  operation actuals  ->  work_order rollup

Specifically:
  - one aggregate labor posting (labor_ticket) is minted per PROGRESSED IN-HOUSE
    step (service_id IS NULL AND act_atl_lab_cost > 0); queued in-house steps and
    outside-service steps get no ticket,
  - each ticket reproduces its step's LABOR to the cent (labor is the anchor and
    the work-order labor rollup is unchanged),
  - BURDEN is re-derived rate-consistently as hours x bur_per_hr_run, where the
    hours are backed out of the step's labor at run_cost_per_hr, and it ties out
    bottom-up: ticket burden == operation burden, summed == work_order burden,
  - the migration is idempotent (a re-run reproduces byte-identical rows).

Run: python hf-space-inventory-sqlgen/tests/test_labor_chain_reconciliation.py
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

# Resource rates used by the fixture (run_cost_per_hr, bur_per_hr_run).
RATES = {"R-FAST": (100.0, 40.0), "R-SLOW": (50.0, 25.0)}

# Smallest schema the migration reads/writes.
_SCHEMA_DDL = """
    CREATE TABLE shop_resource (
        resource_id     TEXT PRIMARY KEY,
        run_cost_per_hr REAL,
        bur_per_hr_run  REAL
    );
    CREATE TABLE work_order (
        wo_id        TEXT PRIMARY KEY,
        act_lab_cost REAL,
        act_bur_cost REAL,
        act_ser_cost REAL
    );
    CREATE TABLE operation (
        rowid_pk         INTEGER PRIMARY KEY,
        wo_id            TEXT,
        sequence_no      INTEGER,
        service_id       INTEGER,
        resource_id      TEXT,
        status           TEXT,
        sched_start_date DATETIME,
        act_atl_lab_cost REAL DEFAULT 0.0,
        act_atl_bur_cost REAL DEFAULT 0.0,
        act_atl_ser_cost REAL DEFAULT 0.0
    );
    CREATE TABLE labor_ticket (
        ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        wo_id       TEXT NOT NULL,
        sequence_no INTEGER NOT NULL,
        employee_id TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        clock_in    DATETIME NOT NULL,
        clock_out   DATETIME NOT NULL,
        total_hours REAL NOT NULL,
        labor_cost  REAL NOT NULL,
        burden_cost REAL NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );
"""


def _build_minimal_db(path):
    """Smallest schema the migration reads/writes, seeded across the cases that
    matter:

      WO1:
        seq 10  in-house  C  R-FAST  labor 1000  -> 10.00 h, burden 400.00
        seq 20  in-house  S  R-SLOW  labor  500  -> 10.00 h, burden 250.00
        seq 30  outside   Q  (svc 501)  labor   0  -> NO ticket, 0 internal
        seq 40  in-house  Q  R-FAST  labor    0  -> NO ticket (queued)
      WO2 (no pre-seeded tickets -> proves zero-ticket coverage):
        seq 10  in-house  C  R-FAST  labor  250  -> 2.50 h, burden 100.00

    The work_order burden is pre-seeded to a deliberately WRONG value (999) to
    prove the migration overwrites it with the rate-consistent rollup; the labor
    is pre-seeded to the true sum so the test can assert labor is left unchanged.
    """
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA_DDL)
    conn.executemany(
        "INSERT INTO shop_resource (resource_id, run_cost_per_hr, bur_per_hr_run) "
        "VALUES (?,?,?)",
        [(rid, r, b) for rid, (r, b) in RATES.items()],
    )
    conn.executemany(
        "INSERT INTO work_order (wo_id, act_lab_cost, act_bur_cost, act_ser_cost) "
        "VALUES (?,?,?,?)",
        [("WO1", 1500.0, 999.0, 0.0), ("WO2", 250.0, 999.0, 0.0)],
    )
    conn.executemany(
        "INSERT INTO operation (rowid_pk, wo_id, sequence_no, service_id, "
        "resource_id, status, sched_start_date, act_atl_lab_cost, act_atl_bur_cost) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (1, "WO1", 10, None, "R-FAST", "C", "2025-01-06", 1000.0, 999.0),
            (2, "WO1", 20, None, "R-SLOW", "S", "2025-01-08", 500.0, 999.0),
            (3, "WO1", 30, 501, None, "Q", "2025-01-09", 0.0, 0.0),
            (4, "WO1", 40, None, "R-FAST", "Q", "2025-01-10", 0.0, 0.0),
            (5, "WO2", 10, None, "R-FAST", "C", "2025-02-03", 250.0, 999.0),
        ],
    )
    conn.commit()
    conn.close()


def _run_migration(db_path):
    mod = importlib.import_module("migrations.backfill_labor_chain")
    mod = importlib.reload(mod)
    mod.DB_PATH = db_path
    mod.run()
    return mod


def _fresh_db():
    tmpdir = tempfile.mkdtemp(prefix="labor_chain_")
    db = os.path.join(tmpdir, "manufacturing.db")
    _build_minimal_db(db)
    return db


def _make_db(resources, work_orders, operations):
    """Build a tiny DB from explicit rows so a test can stage an anomaly.

      resources   -> list[(resource_id, run_cost_per_hr, bur_per_hr_run)]
      work_orders -> list[(wo_id, act_lab_cost, act_bur_cost, act_ser_cost)]
      operations  -> list[(rowid_pk, wo_id, sequence_no, service_id,
                           resource_id, status, sched_start_date,
                           act_atl_lab_cost, act_atl_bur_cost)]
    """
    tmpdir = tempfile.mkdtemp(prefix="labor_chain_")
    db = os.path.join(tmpdir, "manufacturing.db")
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA_DDL)
    conn.executemany(
        "INSERT INTO shop_resource (resource_id, run_cost_per_hr, bur_per_hr_run) "
        "VALUES (?,?,?)",
        resources,
    )
    conn.executemany(
        "INSERT INTO work_order (wo_id, act_lab_cost, act_bur_cost, act_ser_cost) "
        "VALUES (?,?,?,?)",
        work_orders,
    )
    conn.executemany(
        "INSERT INTO operation (rowid_pk, wo_id, sequence_no, service_id, "
        "resource_id, status, sched_start_date, act_atl_lab_cost, act_atl_bur_cost) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        operations,
    )
    conn.commit()
    conn.close()
    return db


# ── tests ────────────────────────────────────────────────────────────────────
def test_one_ticket_per_progressed_inhouse_step():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM labor_ticket").fetchone()[0]
    # outside-service (seq 30) and queued-zero-labor (seq 40) accrue no ticket.
    for wo, seq in (("WO1", 30), ("WO1", 40)):
        c = conn.execute(
            "SELECT COUNT(*) FROM labor_ticket WHERE wo_id=? AND sequence_no=?",
            (wo, seq),
        ).fetchone()[0]
        assert c == 0, f"{wo} seq {seq} should have no ticket, found {c}"
    conn.close()
    assert n == 3, f"expected 3 tickets (the progressed in-house steps), got {n}"
    print("PASS: one ticket per progressed in-house step; none for outside/queued")


def test_tickets_tie_to_operation_labor_and_burden():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    rows = conn.execute(
        """
        SELECT o.wo_id, o.sequence_no,
               ROUND(o.act_atl_lab_cost,2), ROUND(COALESCE(t.tl,0),2),
               ROUND(o.act_atl_bur_cost,2), ROUND(COALESCE(t.tb,0),2)
        FROM operation o
        LEFT JOIN (SELECT wo_id, sequence_no, SUM(labor_cost) tl, SUM(burden_cost) tb
                   FROM labor_ticket GROUP BY wo_id, sequence_no) t
          ON t.wo_id=o.wo_id AND t.sequence_no=o.sequence_no
        WHERE o.service_id IS NULL
        """
    ).fetchall()
    conn.close()
    for wo, seq, ol, tl, ob, tb in rows:
        assert abs(ol - tl) < 0.01, f"{wo} seq {seq}: ticket labor {tl} != op {ol}"
        assert abs(ob - tb) < 0.01, f"{wo} seq {seq}: ticket burden {tb} != op {ob}"
    print("PASS: ticket labor AND burden tie to the operation actuals (per step)")


def test_burden_is_rate_consistent():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT resource_id, total_hours, labor_cost, burden_cost FROM labor_ticket"
    ).fetchall()
    conn.close()
    for rid, hours, lab, bur in rows:
        run_rate, bur_rate = RATES[rid]
        assert abs(bur - round(hours * bur_rate, 2)) < 0.01, (
            f"{rid}: burden {bur} != hours {hours} x bur_rate {bur_rate}"
        )
        # labor reproduces from the same hours within a sub-dollar rounding step.
        assert abs(lab - hours * run_rate) <= run_rate * 0.01 + 0.01, (
            f"{rid}: labor {lab} not consistent with hours {hours} x {run_rate}"
        )
    print("PASS: burden == hours x bur_rate; labor consistent with hours x run_rate")


def test_operation_actuals_roll_up_to_work_order():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    rows = conn.execute(
        """
        SELECT w.wo_id,
               ROUND(w.act_lab_cost,2), ROUND(COALESCE(o.ol,0),2),
               ROUND(w.act_bur_cost,2), ROUND(COALESCE(o.ob,0),2)
        FROM work_order w
        LEFT JOIN (SELECT wo_id, SUM(act_atl_lab_cost) ol, SUM(act_atl_bur_cost) ob
                   FROM operation GROUP BY wo_id) o ON o.wo_id=w.wo_id
        """
    ).fetchall()
    expected_bur = {"WO1": 650.0, "WO2": 100.0}
    expected_lab = {"WO1": 1500.0, "WO2": 250.0}
    conn.close()
    for wo, wl, ol, wb, ob in rows:
        assert abs(wl - ol) < 0.01, f"{wo}: WO labor {wl} != op sum {ol}"
        assert abs(wb - ob) < 0.01, f"{wo}: WO burden {wb} != op sum {ob}"
        assert abs(wl - expected_lab[wo]) < 0.01, f"{wo}: labor {wl} changed (anchor)"
        assert abs(wb - expected_bur[wo]) < 0.01, f"{wo}: burden {wb} != {expected_bur[wo]}"
    print("PASS: operation actuals roll up to work order; labor anchored, burden new")


def test_labor_unchanged_burden_overwritten():
    """Labor headline is preserved; the deliberately-wrong seeded burden (999) is
    replaced by the rate-consistent rollup."""
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    lab, bur = conn.execute(
        "SELECT ROUND(SUM(act_lab_cost),2), ROUND(SUM(act_bur_cost),2) FROM work_order"
    ).fetchone()
    conn.close()
    assert abs(lab - 1750.0) < 0.01, f"total labor {lab} != 1750 (must be unchanged)"
    assert abs(bur - 750.0) < 0.01, f"total burden {bur} != 750 (rate-consistent)"
    print("PASS: labor unchanged (1750); burden overwritten to rate-consistent 750")


def test_clock_and_created_at_are_data_derived():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT clock_in, clock_out, total_hours, created_at FROM labor_ticket"
    ).fetchall()
    conn.close()
    for ci, co, hours, created in rows:
        assert hours > 0, f"non-positive hours {hours}"
        assert co > ci, f"clock_out {co} not after clock_in {ci}"
        assert created == co, f"created_at {created} should equal clock_out {co}"
    print("PASS: clock_out > clock_in, hours > 0, created_at is data-derived")


def test_migration_is_idempotent():
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    first_t = conn.execute("SELECT * FROM labor_ticket ORDER BY ticket_id").fetchall()
    first_o = conn.execute(
        "SELECT rowid_pk, act_atl_bur_cost FROM operation ORDER BY rowid_pk"
    ).fetchall()
    first_w = conn.execute(
        "SELECT wo_id, act_lab_cost, act_bur_cost FROM work_order ORDER BY wo_id"
    ).fetchall()
    conn.close()

    _run_migration(db)
    conn = sqlite3.connect(db)
    second_t = conn.execute("SELECT * FROM labor_ticket ORDER BY ticket_id").fetchall()
    second_o = conn.execute(
        "SELECT rowid_pk, act_atl_bur_cost FROM operation ORDER BY rowid_pk"
    ).fetchall()
    second_w = conn.execute(
        "SELECT wo_id, act_lab_cost, act_bur_cost FROM work_order ORDER BY wo_id"
    ).fetchall()
    conn.close()

    assert first_t == second_t, "labor_ticket rows differ on re-run (not idempotent)"
    assert first_o == second_o, "operation burden differs on re-run (not idempotent)"
    assert first_w == second_w, "work_order rollup differs on re-run (not idempotent)"
    print("PASS: migration is idempotent (re-run reproduces identical rows)")


def test_zero_ticket_work_order_gets_covered():
    """WO2 had no pre-seeded tickets; the rebuild still mints its labor posting."""
    db = _fresh_db()
    _run_migration(db)
    conn = sqlite3.connect(db)
    n = conn.execute(
        "SELECT COUNT(*) FROM labor_ticket WHERE wo_id='WO2'"
    ).fetchone()[0]
    conn.close()
    assert n == 1, f"WO2 should be covered by 1 ticket, got {n}"
    print("PASS: a work order with no prior tickets is covered by the rebuild")


def test_fails_closed_on_missing_run_rate():
    """A progressed in-house step on a resource with no run rate cannot have its
    hours backed out; the migration must abort (rollback) rather than drop that
    step's labor from the ticket rollup."""
    db = _make_db(
        resources=[("R-NORATE", 0.0, 30.0)],
        work_orders=[("WO1", 500.0, 999.0, 0.0)],
        operations=[(1, "WO1", 10, None, "R-NORATE", "C", "2025-01-06", 500.0, 999.0)],
    )
    try:
        _run_migration(db)
    except RuntimeError as e:
        assert "run rate" in str(e), f"unexpected abort reason: {e}"
    else:
        raise AssertionError("migration should have aborted on a missing run rate")
    # Nothing was committed: the deliberately-wrong burden (999) is untouched.
    conn = sqlite3.connect(db)
    bur = conn.execute("SELECT act_bur_cost FROM work_order WHERE wo_id='WO1'").fetchone()[0]
    n = conn.execute("SELECT COUNT(*) FROM labor_ticket").fetchone()[0]
    conn.close()
    assert bur == 999.0 and n == 0, "a failed run must leave the DB untouched"
    print("PASS: aborts (rollback) on a progressed step with no run rate")


def test_fails_closed_on_labor_rounding_to_zero_hours():
    """Labor so small it rounds to 0.00 hours would mint a zero-duration ticket and
    zero burden — the rate model breaks, so the migration must abort."""
    db = _make_db(
        resources=[("R-FAST", 100.0, 40.0)],
        # 0.4 / 100 = 0.004 h -> rounds to 0.00 h
        work_orders=[("WO1", 0.4, 999.0, 0.0)],
        operations=[(1, "WO1", 10, None, "R-FAST", "C", "2025-01-06", 0.4, 999.0)],
    )
    try:
        _run_migration(db)
    except RuntimeError as e:
        assert "0.00 hours" in str(e), f"unexpected abort reason: {e}"
    else:
        raise AssertionError("migration should have aborted on labor that rounds to 0 hours")
    print("PASS: aborts on positive labor that rounds to zero hours")


def test_fails_closed_when_labor_bearing_wo_has_no_operations():
    """A work order carrying labor but with NO operations would be silently zeroed
    by the rollup; the anchor invariant must catch it and abort."""
    db = _make_db(
        resources=[("R-FAST", 100.0, 40.0)],
        # WO2 has labor on its rollup but no operation rows.
        work_orders=[("WO1", 1000.0, 999.0, 0.0), ("WO2", 750.0, 999.0, 0.0)],
        operations=[(1, "WO1", 10, None, "R-FAST", "C", "2025-01-06", 1000.0, 999.0)],
    )
    try:
        _run_migration(db)
    except RuntimeError as e:
        assert "labor headline changed" in str(e), f"unexpected abort reason: {e}"
    else:
        raise AssertionError("migration should have aborted when a labor-bearing WO has no operations")
    # WO2's labor was NOT zeroed because the whole run rolled back.
    conn = sqlite3.connect(db)
    lab = conn.execute("SELECT act_lab_cost FROM work_order WHERE wo_id='WO2'").fetchone()[0]
    conn.close()
    assert lab == 750.0, "the failed run must not have zeroed the orphan WO's labor"
    print("PASS: aborts when a labor-bearing work order has no operations")


def main() -> int:
    tests = [
        test_one_ticket_per_progressed_inhouse_step,
        test_tickets_tie_to_operation_labor_and_burden,
        test_burden_is_rate_consistent,
        test_operation_actuals_roll_up_to_work_order,
        test_labor_unchanged_burden_overwritten,
        test_clock_and_created_at_are_data_derived,
        test_migration_is_idempotent,
        test_zero_ticket_work_order_gets_covered,
        test_fails_closed_on_missing_run_rate,
        test_fails_closed_on_labor_rounding_to_zero_hours,
        test_fails_closed_when_labor_bearing_wo_has_no_operations,
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
