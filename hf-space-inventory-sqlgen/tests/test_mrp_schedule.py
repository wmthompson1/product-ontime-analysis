"""Tests for the MRP demand-supply schedule grid (mrp_engine.compute_mrp_grid).

These are pure, deterministic unit tests over a small in-memory-style fixture DB
(temp file) seeded with controlled demand + supply. They lock in:

  * the netting math (gross / scheduled / projected-available / net / planned
    receipts / planned releases) across Past Due + 6 monthly buckets,
  * the lead-time offset (a planned receipt in one bucket releases earlier),
  * the DATA-DERIVED as-of anchor (MAX(work_order.close_date)) — never wall clock,
  * bucket boundaries, and
  * fail-closed behavior (unknown part, non-positive/absent lead time, missing
    planning columns) raising ValueError instead of planning against zero.

Run: python hf-space-inventory-sqlgen/tests/test_mrp_schedule.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import mrp_engine as mrp  # noqa: E402

# Anchor: a closed work order dated here fixes AS_OF regardless of the wall clock.
AS_OF = "2026-05-31"

EXPECTED_COLUMNS = [
    "Past Due",
    "May 2026",
    "Jun 2026",
    "Jul 2026",
    "Aug 2026",
    "Sep 2026",
    "Oct 2026",
]

# Hand-computed grid for part P1 (lead 30d, on-hand 10):
#   demand:  3 @ 2026-04-01 (Past Due), 5 @ 2026-05-15 (M0), 20 @ 2026-06-15 (M1)
#   supply:  PO 4 @ 2026-05-20 (M0), WO 8 @ 2026-06-10 (M1)
EXPECTED = {
    "Gross Requirements":            [3, 5, 20, 0, 0, 0, 0],
    "Scheduled Receipts":            [0, 4, 8, 0, 0, 0, 0],
    "Projected Available Balance":   [7, 6, 0, 0, 0, 0, 0],
    "Net Requirements":              [0, 0, 6, 0, 0, 0, 0],
    "Planned Order Receipts":        [0, 0, 6, 0, 0, 0, 0],
    # release of the Jun (M1) receipt is pulled 30 days earlier into May (M0)
    "Planned Order Releases":        [0, 6, 0, 0, 0, 0, 0],
}


def _seed(conn: sqlite3.Connection, *, with_need_by: bool = True) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE part (
            part_id TEXT PRIMARY KEY,
            part_class TEXT,
            lead_time_days INTEGER,
            on_hand_qty INTEGER
        );
        CREATE TABLE customer_order (order_id TEXT PRIMARY KEY, status TEXT);
        CREATE TABLE work_order (
            wo_id TEXT PRIMARY KEY, part_id TEXT, status TEXT,
            required_date TEXT, close_date TEXT, quantity INTEGER
        );
        CREATE TABLE purchase_order (
            po_id TEXT PRIMARY KEY, status TEXT, required_date TEXT
        );
        CREATE TABLE po_line (
            line_id INTEGER PRIMARY KEY, po_id TEXT, part_id TEXT, quantity INTEGER
        );
        """
    )
    if with_need_by:
        cur.executescript(
            """
            CREATE TABLE customer_order_line (
                order_line_id INTEGER PRIMARY KEY, order_id TEXT, part_id TEXT,
                order_qty INTEGER, need_by_date TEXT, desired_release_date TEXT
            );
            """
        )
    else:  # older schema: no MRP demand columns → must fail closed
        cur.executescript(
            """
            CREATE TABLE customer_order_line (
                order_line_id INTEGER PRIMARY KEY, order_id TEXT, part_id TEXT,
                order_qty INTEGER
            );
            """
        )

    # Parts: P1 plannable; P2 zero lead; P3 null lead (both used for fail-closed).
    cur.executemany(
        "INSERT INTO part (part_id, part_class, lead_time_days, on_hand_qty) VALUES (?,?,?,?)",
        [
            ("P1", "BUY", 30, 10),
            ("P2", "BUY", 0, 5),
            ("P3", "MAKE", None, 5),
        ],
    )

    # A CLOSED work order fixes AS_OF (never a scheduled receipt).
    cur.execute(
        "INSERT INTO work_order (wo_id, part_id, status, required_date, close_date, quantity) "
        "VALUES ('WO-CLOSED', 'PX', 'closed', NULL, ?, 1)",
        (AS_OF,),
    )
    # Non-closed WO supply for P1 in Jun (M1).
    cur.execute(
        "INSERT INTO work_order (wo_id, part_id, status, required_date, close_date, quantity) "
        "VALUES ('WO-SUP', 'P1', 'released', '2026-06-10', NULL, 8)"
    )

    # Open PO supply for P1 in May (M0).
    cur.execute("INSERT INTO purchase_order (po_id, status, required_date) VALUES ('PO1', 'Open', '2026-05-20')")
    cur.execute("INSERT INTO po_line (line_id, po_id, part_id, quantity) VALUES (1, 'PO1', 'P1', 4)")

    if with_need_by:
        cur.execute("INSERT INTO customer_order (order_id, status) VALUES ('CO1', 'Open')")
        cur.executemany(
            "INSERT INTO customer_order_line "
            "(order_line_id, order_id, part_id, order_qty, need_by_date, desired_release_date) "
            "VALUES (?,?,?,?,?,?)",
            [
                (1, "CO1", "P1", 3, "2026-04-01", None),   # Past Due
                (2, "CO1", "P1", 5, "2026-05-15", None),   # M0
                (3, "CO1", "P1", 20, "2026-06-15", None),  # M1
            ],
        )
    conn.commit()


_PATHS: dict[int, str] = {}


def _fixture(*, with_need_by: bool = True) -> sqlite3.Connection:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    _PATHS[id(conn)] = path
    _seed(conn, with_need_by=with_need_by)
    return conn


def _blank_conn() -> sqlite3.Connection:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    _PATHS[id(conn)] = path
    return conn


def _cleanup(conn: sqlite3.Connection) -> None:
    path = _PATHS.pop(id(conn), None)
    conn.close()
    if path and os.path.exists(path):
        os.remove(path)


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
def test_data_derived_anchor_not_wall_clock():
    conn = _fixture()
    try:
        as_of = mrp.compute_as_of(conn)
        assert as_of == date(2026, 5, 31), f"as_of should be data-derived, got {as_of}"
        assert as_of != date.today(), "as_of must not track the wall clock"
        assert mrp.plan_start(as_of) == date(2026, 5, 1)
    finally:
        _cleanup(conn)


def test_bucket_boundaries():
    buckets = mrp.month_buckets(date(2026, 5, 31))
    assert len(buckets) == 6, f"expected 6 buckets, got {len(buckets)}"
    assert [b[0] for b in buckets] == EXPECTED_COLUMNS[1:]
    # membership is [start, end)
    assert mrp.bucket_index_for(date(2026, 5, 1), buckets) == 0
    assert mrp.bucket_index_for(date(2026, 6, 1), buckets) == 1
    assert mrp.bucket_index_for(date(2026, 4, 30), buckets) is None  # before horizon
    assert mrp.bucket_index_for(date(2026, 11, 1), buckets) is None  # after horizon


def test_grid_netting_math():
    conn = _fixture()
    try:
        grid = mrp.compute_mrp_grid(conn, "P1")
        assert grid["columns"] == EXPECTED_COLUMNS, grid["columns"]
        assert grid["as_of"] == date(2026, 5, 31)
        assert grid["lead_time_days"] == 30
        assert grid["on_hand_qty"] == 10
        rows = dict(grid["rows"])
        for label, expected in EXPECTED.items():
            assert rows[label] == expected, f"{label}: got {rows[label]}, want {expected}"
        # lot-for-lot invariant
        assert rows["Planned Order Receipts"] == rows["Net Requirements"]
    finally:
        _cleanup(conn)


def test_lead_time_offset_pulls_release_earlier():
    conn = _fixture()
    try:
        grid = mrp.compute_mrp_grid(conn, "P1")
        rows = dict(grid["rows"])
        receipts = rows["Planned Order Receipts"]
        releases = rows["Planned Order Releases"]
        # The single planned receipt lands in Jun (index 2)...
        assert receipts.index(6) == 2
        # ...but its release is pulled 30 days earlier into May (index 1).
        assert releases.index(6) == 1
        # releases conserve the total receipts
        assert sum(releases) == sum(receipts) == 6
    finally:
        _cleanup(conn)


def test_list_planning_parts_only_in_horizon_demand():
    conn = _fixture()
    try:
        parts = mrp.list_planning_parts(conn)
        ids = {p["part_id"] for p in parts}
        assert ids == {"P1"}, f"only P1 has in-horizon demand, got {ids}"
        p1 = parts[0]
        # Past-due (Apr) demand is excluded; 5 (M0) + 20 (M1) = 25
        assert p1["demand_qty"] == 25, p1["demand_qty"]
    finally:
        _cleanup(conn)


def test_validate_planning_inputs_passes_on_plannable_fixture():
    conn = _fixture()
    try:
        summary = mrp.validate_planning_inputs(conn)
        assert summary["demand_parts"] == 1
        assert summary["as_of"] == date(2026, 5, 31)
    finally:
        _cleanup(conn)


def test_fail_closed_unknown_part():
    conn = _fixture()
    try:
        _expect_valueerror(lambda: mrp.compute_mrp_grid(conn, "NOPE"), "unknown part")
    finally:
        _cleanup(conn)


def test_fail_closed_non_positive_lead():
    conn = _fixture()
    try:
        _expect_valueerror(lambda: mrp.compute_mrp_grid(conn, "P2"), "zero lead time")
    finally:
        _cleanup(conn)


def test_fail_closed_absent_lead():
    conn = _fixture()
    try:
        _expect_valueerror(lambda: mrp.compute_mrp_grid(conn, "P3"), "null lead time")
    finally:
        _cleanup(conn)


def test_fail_closed_missing_columns():
    conn = _fixture(with_need_by=False)
    try:
        _expect_valueerror(lambda: mrp.compute_mrp_grid(conn, "P1"), "missing need_by_date")
    finally:
        _cleanup(conn)


def test_fractional_qty_and_release_folds_into_past_due():
    """Fractional quantities flow through, and a long lead pulls an M0 receipt's
    release before PLAN_START so it folds into Past Due."""
    conn = _blank_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE part (part_id TEXT PRIMARY KEY, part_class TEXT,
                lead_time_days INTEGER, on_hand_qty REAL);
            CREATE TABLE customer_order (order_id TEXT PRIMARY KEY, status TEXT);
            CREATE TABLE customer_order_line (order_line_id INTEGER PRIMARY KEY,
                order_id TEXT, part_id TEXT, order_qty REAL, need_by_date TEXT,
                desired_release_date TEXT);
            CREATE TABLE work_order (wo_id TEXT PRIMARY KEY, part_id TEXT, status TEXT,
                required_date TEXT, close_date TEXT, quantity REAL);
            CREATE TABLE purchase_order (po_id TEXT PRIMARY KEY, status TEXT, required_date TEXT);
            CREATE TABLE po_line (line_id INTEGER PRIMARY KEY, po_id TEXT, part_id TEXT, quantity REAL);
            """
        )
        conn.execute("INSERT INTO part VALUES ('FX', 'BUY', 45, 5.5)")
        conn.execute(
            "INSERT INTO work_order (wo_id, part_id, status, required_date, close_date, quantity) "
            "VALUES ('WO-CLOSED', 'PX', 'closed', NULL, ?, 1)",
            (AS_OF,),
        )
        conn.execute("INSERT INTO customer_order VALUES ('CO1', 'Open')")
        conn.execute(
            "INSERT INTO customer_order_line "
            "(order_line_id, order_id, part_id, order_qty, need_by_date, desired_release_date) "
            "VALUES (1, 'CO1', 'FX', 10.5, '2026-05-10', NULL)"
        )
        conn.commit()

        grid = mrp.compute_mrp_grid(conn, "FX")
        rows = dict(grid["rows"])
        assert rows["Gross Requirements"] == [0, 10.5, 0, 0, 0, 0, 0]
        assert rows["Net Requirements"] == [0, 5.0, 0, 0, 0, 0, 0]
        assert rows["Projected Available Balance"] == [5.5, 0.0, 0, 0, 0, 0, 0]
        # 45-day lead pulls the May (M0) receipt's release before PLAN_START → Past Due
        assert rows["Planned Order Releases"] == [5.0, 0, 0, 0, 0, 0, 0]
        assert sum(rows["Planned Order Releases"]) == sum(rows["Planned Order Receipts"]) == 5.0
    finally:
        _cleanup(conn)


def _expect_valueerror(fn, label):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(f"expected ValueError ({label}), none raised")


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
def main() -> int:
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
    print(f"\n{total - failures}/{total} MRP schedule tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
