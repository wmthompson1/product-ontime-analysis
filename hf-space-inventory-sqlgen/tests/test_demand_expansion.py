"""Tests for the demand-side expansion against the REAL manufacturing.db
(migrations/expand_demand_and_completions.py output).

These lock in the data contract:

  * the three completed shop orders (WO-00007 / WO-00015 / WO-00009) are
    closed with in-band close dates and every operation complete,
  * AS_OF (MAX(work_order.close_date)) never moved past 2026-01-21 — the
    completions anchor to it, they do not drag it,
  * work-order and customer-order header counts stay inside the demo band
    [10, 20],
  * the MRP demo work orders (WO-MRP-*) are all still open,
  * the three new customer orders exist, are Open, and carry exactly the
    expected line counts with in-horizon need-by dates,
  * every part demanded by the new orders holds on-hand stock (the real
    supply basis the fail-closed planning gate requires),
  * work-order cost rollups reconcile to operation actuals to the cent for
    EVERY work order (the outside-service key repair closed that gap),
  * mrp_engine.validate_planning_inputs passes on the live database,
  * the migration is idempotent (a re-run changes nothing).

Run: python hf-space-inventory-sqlgen/tests/test_demand_expansion.py
Skips (exit 0 with a notice) if manufacturing.db is missing — fresh clones
build it with scripts/bootstrap_db.py.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import mrp_engine as mrp  # noqa: E402

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

COMPLETED_WOS = {
    "WO-00007": "2026-01-14",
    "WO-00015": "2026-01-20",
    "WO-00009": "2026-01-21",
}
NEW_ORDERS = {"CO-00016": 7, "CO-00017": 7, "CO-00018": 6}
AS_OF_CEILING = "2026-01-21"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_completed_wos_closed_with_ops_done():
    conn = _connect()
    try:
        for wo_id, close_dt in COMPLETED_WOS.items():
            row = conn.execute(
                "SELECT status, close_date FROM work_order WHERE wo_id=?",
                (wo_id,),
            ).fetchone()
            assert row, f"{wo_id} missing"
            assert row[0] == "closed", f"{wo_id} status {row[0]}"
            assert row[1] == close_dt, f"{wo_id} close_date {row[1]} != {close_dt}"
            open_ops = _one(conn, """
                SELECT COUNT(*) FROM operation
                WHERE wo_id=? AND (status<>'C' OR close_date IS NULL)
            """, (wo_id,))
            assert open_ops == 0, f"{wo_id}: {open_ops} incomplete op(s)"
    finally:
        conn.close()


def test_as_of_anchor_unmoved():
    """The completions must anchor to AS_OF, never define it: the latest
    completed-WO close date is <= the latest close date among all OTHER
    work orders (so removing the completions would not move AS_OF)."""
    conn = _connect()
    try:
        marks = ",".join("?" * len(COMPLETED_WOS))
        ours = _one(conn,
                    f"SELECT MAX(close_date) FROM work_order WHERE wo_id IN ({marks})",
                    tuple(COMPLETED_WOS))
        others = _one(conn,
                      f"SELECT MAX(close_date) FROM work_order WHERE wo_id NOT IN ({marks})",
                      tuple(COMPLETED_WOS))
        assert ours and others, "close dates missing"
        assert ours[:10] <= others[:10], (
            f"completions drag AS_OF: {ours} > pre-existing max {others}")
        assert ours[:10] <= AS_OF_CEILING, f"AS_OF ceiling breached: {ours}"
    finally:
        conn.close()


def test_header_bands_respected():
    conn = _connect()
    try:
        # Band applies to FIRM shop orders; planned (unreleased) orders are
        # the MRP proposal population and scale separately
        # (migrations/add_planned_work_orders.py). The protected July
        # daily-throughput series (WO-JUL-% / CO-JUL-%,
        # seed_july_throughput.py) sits outside the bands by design.
        wo = _one(conn, "SELECT COUNT(*) FROM work_order "
                        "WHERE status IN ('firmed','released','closed') "
                        "AND wo_id NOT LIKE 'WO-JUL-%'")
        co = _one(conn, "SELECT COUNT(*) FROM customer_order "
                        "WHERE order_id NOT LIKE 'CO-JUL-%'")
        assert 10 <= wo <= 20, f"firm work-order headers out of band: {wo}"
        assert 10 <= co <= 20, f"customer-order headers out of band: {co}"
    finally:
        conn.close()


def test_mrp_demo_wos_still_open():
    conn = _connect()
    try:
        n = _one(conn, """
            SELECT COUNT(*) FROM work_order
            WHERE wo_id LIKE 'WO-MRP-%' AND status='closed'
        """)
        assert n == 0, f"{n} MRP demo WO(s) were closed"
    finally:
        conn.close()


def test_new_customer_orders_and_lines():
    conn = _connect()
    try:
        as_of = mrp.compute_as_of(conn)
        buckets = mrp.month_buckets(as_of)
        hs, he = mrp.horizon_bounds(buckets)
        for order_id, expected_lines in NEW_ORDERS.items():
            st = conn.execute(
                "SELECT status FROM customer_order WHERE order_id=?",
                (order_id,),
            ).fetchone()
            assert st and st[0] == "Open", f"{order_id} missing or not Open"
            rows = conn.execute("""
                SELECT l.part_id, l.order_qty, l.need_by_date, p.on_hand_qty
                FROM customer_order_line l JOIN part p ON p.part_id=l.part_id
                WHERE l.order_id=?
            """, (order_id,)).fetchall()
            assert len(rows) == expected_lines, (
                f"{order_id}: {len(rows)} lines != {expected_lines}")
            for part_id, qty, need_by, on_hand in rows:
                assert qty > 0, f"{order_id}/{part_id}: non-positive qty"
                assert hs.isoformat() <= need_by < he.isoformat(), (
                    f"{order_id}/{part_id}: need_by {need_by} out of horizon")
                assert (on_hand or 0) > 0, (
                    f"{order_id}/{part_id}: no on-hand supply basis")
    finally:
        conn.close()


def test_wo_rollups_reconcile_to_op_actuals():
    conn = _connect()
    try:
        drift = _one(conn, """
            SELECT COUNT(*) FROM work_order w
            WHERE ABS(COALESCE(w.act_lab_cost,0) + COALESCE(w.act_bur_cost,0)
                      + COALESCE(w.act_ser_cost,0)
                  - (SELECT COALESCE(SUM(o.act_atl_lab_cost + o.act_atl_bur_cost
                                         + o.act_atl_ser_cost), 0)
                     FROM operation o WHERE o.wo_id = w.wo_id)) > 0.01
        """)
        assert drift == 0, f"{drift} work order(s) with op-actuals drift"
    finally:
        conn.close()


def test_planning_gate_passes():
    """The fail-closed gate passes AND every part the new orders demand is
    actually a planning part (invariant-based, no magic count)."""
    sys.path.insert(0, os.path.join(HF_DIR, "migrations"))
    import expand_demand_and_completions as mig

    expected_parts = {
        part_id
        for lines in mig.NEW_LINES.values()
        for (part_id, _qty, _offset) in lines
    }
    conn = _connect()
    try:
        mrp.validate_planning_inputs(conn)  # raises ValueError on failure
        planning = {p["part_id"] for p in mrp.list_planning_parts(conn)}
        missing = expected_parts - planning
        assert not missing, f"new-demand parts not in planning list: {missing}"
    finally:
        conn.close()


def test_migration_idempotent():
    conn = _connect()
    try:
        before = (
            _one(conn, "SELECT COUNT(*) FROM customer_order"),
            _one(conn, "SELECT COUNT(*) FROM customer_order_line"),
            _one(conn, "SELECT COUNT(*) FROM labor_ticket"),
            _one(conn, "SELECT COALESCE(SUM(on_hand_qty),0) FROM part"),
            _one(conn, "SELECT MAX(close_date) FROM work_order"),
        )
    finally:
        conn.close()
    r = subprocess.run(
        [sys.executable, os.path.join(HF_DIR, "migrations",
                                      "expand_demand_and_completions.py")],
        cwd=HF_DIR, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"re-run failed:\n{r.stdout}\n{r.stderr}"
    conn = _connect()
    try:
        after = (
            _one(conn, "SELECT COUNT(*) FROM customer_order"),
            _one(conn, "SELECT COUNT(*) FROM customer_order_line"),
            _one(conn, "SELECT COUNT(*) FROM labor_ticket"),
            _one(conn, "SELECT COALESCE(SUM(on_hand_qty),0) FROM part"),
            _one(conn, "SELECT MAX(close_date) FROM work_order"),
        )
    finally:
        conn.close()
    assert before == after, f"re-run changed data: {before} -> {after}"


def main() -> int:
    if not os.path.exists(DB_PATH):
        print("SKIP  manufacturing.db missing — run scripts/bootstrap_db.py first")
        return 0
    conn = _connect()
    try:
        seen = conn.execute(
            "SELECT COUNT(*) FROM customer_order WHERE order_id='CO-00016'"
        ).fetchone()[0]
    finally:
        conn.close()
    if not seen:
        print("SKIP  demand expansion not present — run "
              "migrations/expand_demand_and_completions.py first")
        return 0

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {t.__name__}: {exc}")
    total = len(tests)
    print(f"\n{total - failures}/{total} demand-expansion tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
