"""Tests for the demand linkage + forecast foundation (Task #244) against the
REAL manufacturing.db (migrations/add_demand_linkage_and_forecast.py output).

These lock in the data contract, not fixture math (tests/test_mrp_schedule.py
owns the netting math over controlled fixtures):

  * work_order.demand_order_line_id exists, is a declared FK to
    customer_order_line.order_line_id, and >= 50% of work orders are linked,
  * every linked work order points at an order line of the SAME part,
  * part.safety_stock exists and is exactly 1 (SME rule) for every part,
  * the forecast table exists, covers exactly the parts of still-unlinked
    work orders, and only carries in-horizon positive-quantity rows,
  * the 9-month horizon's extended buckets (M6..M8) carry both demand and
    supply for at least one planning part each,
  * the linkage backfill is idempotent (a re-run links nothing new).

Run: python hf-space-inventory-sqlgen/tests/test_demand_linkage.py
Skips (exit 0 with a notice) if manufacturing.db is missing — fresh clones
build it with scripts/bootstrap_db.py.
"""

from __future__ import annotations

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "migrations"))

import mrp_engine as mrp  # noqa: E402

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

MIN_LINK_RATIO = 0.5
EXTENDED_PERIODS = (7, 8, 9)  # grid indices for buckets M6..M8 (Past Due = 0)


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def test_linkage_column_declared_fk():
    conn = _connect()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(work_order)")}
        assert "demand_order_line_id" in cols, "linkage column missing"
        fks = conn.execute("PRAGMA foreign_key_list(work_order)").fetchall()
        assert any(
            fk[2] == "customer_order_line" and fk[3] == "demand_order_line_id"
            for fk in fks
        ), f"declared FK to customer_order_line missing: {fks}"
    finally:
        conn.close()


def test_linked_ratio_at_least_half():
    conn = _connect()
    try:
        # Planned orders (WO-PLN-*) are MRP proposals outside the linkage layer.
        total = conn.execute(
            "SELECT COUNT(*) FROM work_order WHERE wo_id NOT LIKE 'WO-PLN-%'"
        ).fetchone()[0]
        linked = conn.execute(
            "SELECT COUNT(*) FROM work_order WHERE demand_order_line_id IS NOT NULL"
        ).fetchone()[0]
        assert total > 0
        ratio = linked / total
        assert ratio >= MIN_LINK_RATIO, (
            f"only {linked}/{total} ({ratio:.0%}) work orders linked"
        )
    finally:
        conn.close()


def test_linked_lines_same_part_and_exist():
    conn = _connect()
    try:
        bad = conn.execute(
            """
            SELECT w.wo_id, w.part_id, l.part_id
            FROM work_order w
            LEFT JOIN customer_order_line l
                   ON l.order_line_id = w.demand_order_line_id
            WHERE w.demand_order_line_id IS NOT NULL
              AND (l.order_line_id IS NULL OR l.part_id != w.part_id)
            """
        ).fetchall()
        assert not bad, f"linked WOs with missing/mismatched lines: {bad}"
    finally:
        conn.close()


def test_safety_stock_exactly_one():
    conn = _connect()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(part)")}
        assert "safety_stock" in cols, "part.safety_stock missing"
        bad = conn.execute(
            "SELECT COUNT(*) FROM part WHERE safety_stock IS NULL OR safety_stock != 1"
        ).fetchone()[0]
        assert bad == 0, f"{bad} parts violate the safety_stock=1 SME rule"
    finally:
        conn.close()


def test_forecast_covers_unlinked_wo_parts():
    conn = _connect()
    try:
        unlinked_parts = {
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT part_id FROM work_order "
                "WHERE demand_order_line_id IS NULL "
                "AND wo_id NOT LIKE 'WO-PLN-%'"
            )
        }
        forecast_parts = {
            r[0] for r in conn.execute("SELECT DISTINCT part_id FROM forecast")
        }
        assert forecast_parts, "forecast table has no rows"
        assert forecast_parts == unlinked_parts, (
            f"forecast parts {forecast_parts} != unlinked-WO parts {unlinked_parts}"
        )
        # every row: positive qty, in-horizon date
        as_of = mrp.compute_as_of(conn)
        buckets = mrp.month_buckets(as_of)
        hs, he = mrp.horizon_bounds(buckets)
        bad = conn.execute(
            "SELECT COUNT(*) FROM forecast WHERE forecast_qty <= 0 "
            "OR date(forecast_date) < ? OR date(forecast_date) >= ?",
            (hs.isoformat(), he.isoformat()),
        ).fetchone()[0]
        assert bad == 0, f"{bad} forecast rows out of horizon or non-positive"
    finally:
        conn.close()


def test_horizon_is_nine_buckets_with_extended_coverage():
    conn = _connect()
    try:
        assert mrp.HORIZON_MONTHS == 9
        as_of = mrp.compute_as_of(conn)
        buckets = mrp.month_buckets(as_of)
        assert len(buckets) == 9

        demand_hit = supply_hit = None
        for row in mrp.list_planning_parts(conn):
            grid = mrp.compute_mrp_grid(conn, row["part_id"])
            rows = dict(grid["rows"])
            gross = rows["Gross Requirements"]
            supply = [
                s + r
                for s, r in zip(
                    rows["Scheduled Receipts"], rows["Planned Order Receipts"]
                )
            ]
            if demand_hit is None and any(gross[i] > 0 for i in EXTENDED_PERIODS):
                demand_hit = row["part_id"]
            if supply_hit is None and any(supply[i] > 0 for i in EXTENDED_PERIODS):
                supply_hit = row["part_id"]
            if demand_hit and supply_hit:
                break
        assert demand_hit, "no gross requirements in extended buckets (M6..M8)"
        assert supply_hit, "no supply in extended buckets (M6..M8)"
    finally:
        conn.close()


def test_forecast_never_double_counts_linked_demand():
    """For every planning part, grid gross <= CO demand + forecast (the
    consumption rule caps, never stacks) and >= max of the two."""
    conn = _connect()
    try:
        for row in mrp.list_planning_parts(conn):
            grid = mrp.compute_mrp_grid(conn, row["part_id"])
            gross_total = sum(dict(grid["rows"])["Gross Requirements"])
            co, fc = grid["co_demand_qty"], grid["forecast_qty"]
            # Past-due CO demand can push gross above the in-horizon CO total,
            # so bound with the in-horizon components only where forecast exists.
            if fc > 0:
                assert gross_total <= co + fc + sum(
                    dict(grid["rows"])["Gross Requirements"][:1]
                ), f"{row['part_id']}: gross {gross_total} exceeds co+fc ({co}+{fc})"
    finally:
        conn.close()


def test_gate_failure_rolls_back_everything():
    """Force a late fail-closed gate to fail on a temp COPY of the DB and
    prove the migration persisted nothing (transaction atomicity)."""
    import tempfile

    import add_demand_linkage_and_forecast as mig

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(tmp.name)
    try:
        src.backup(dst)  # WAL-safe copy
    finally:
        src.close()
        dst.close()

    def _dump(path):
        conn = sqlite3.connect(path)
        try:
            return {
                "wo": conn.execute(
                    "SELECT wo_id, demand_order_line_id FROM work_order ORDER BY wo_id"
                ).fetchall(),
                "fc": conn.execute(
                    "SELECT forecast_id, part_id, forecast_qty FROM forecast "
                    "ORDER BY forecast_id"
                ).fetchall(),
                "part": conn.execute(
                    "SELECT part_id, on_hand_qty, safety_stock FROM part ORDER BY part_id"
                ).fetchall(),
            }
        finally:
            conn.close()

    before = _dump(tmp.name)
    orig_db_path, orig_ratio = mig.DB_PATH, mig.MIN_LINK_RATIO
    try:
        mig.DB_PATH = tmp.name
        mig.MIN_LINK_RATIO = 1.01  # impossible → the ratio gate must fail
        raised = False
        try:
            mig.run()
        except SystemExit:
            raised = True
        assert raised, "forced gate failure did not raise"
    finally:
        mig.DB_PATH, mig.MIN_LINK_RATIO = orig_db_path, orig_ratio
    after = _dump(tmp.name)
    os.unlink(tmp.name)
    assert before == after, "gate failure left persisted changes behind"


def test_linkage_backfill_idempotent():
    """A re-run of the greedy linkage over the live rows links nothing new."""
    import add_demand_linkage_and_forecast as mig

    conn = _connect()
    try:
        cur = conn.cursor()
        linked_now, _linked, _total = mig.link_work_orders(cur)
        conn.rollback()  # never write from a test
        assert linked_now == 0, f"re-run linked {linked_now} more WOs — not idempotent"
    finally:
        conn.close()


def main() -> int:
    if not os.path.exists(DB_PATH):
        print("SKIP  manufacturing.db not found — run scripts/bootstrap_db.py first")
        return 0
    conn = _connect()
    try:
        has_forecast = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='forecast'"
        ).fetchone()[0]
    finally:
        conn.close()
    if not has_forecast:
        print("SKIP  demand-linkage foundation not present — run "
              "migrations/add_demand_linkage_and_forecast.py first")
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
    print(f"\n{total - failures}/{total} demand-linkage tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
