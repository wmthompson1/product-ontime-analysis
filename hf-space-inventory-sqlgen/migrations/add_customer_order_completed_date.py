"""
Migration: add customer_order.completed_date (DATE, nullable) and backfill it.

Why: management asked (Customer perspective) for monthly orders vs monthly
completed orders, in time buckets, for 2025. The synthetic ERP tracked only a
completion STATUS (Shipped / Closed) on customer_order with no date for the
event, so a monthly "completed" series had nothing to ground on. This adds
the missing completion date so the governed view
(app_schema/ground_truth/sql_snippets/customer_monthlyorderscompleted_20260704_000006.sql)
can run against the synthetic ERP.

Backfill is DETERMINISTIC and GROUNDED to real ERP semantics (no randomness):
  completed_date = date(order_date, '+' || MAX(part.lead_time_days) || ' days')
  where MAX is taken across the order's lines — i.e. an order completes when
  its longest-lead-time part completes, which is exactly how an ERP projects
  a completion from lead time. Only Shipped/Closed orders get a date;
  Open and Cancelled orders stay NULL (they never completed).

Preconditions verified before writing: every Shipped/Closed order has at
least one line, and every such line's part has a positive lead_time_days.
The backfill FAILS CLOSED (raises) if any Shipped/Closed order would end up
without a completed_date.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_customer_order_completed_date.py

Safe to re-run: the column add is skipped if it already exists, and the
backfill only touches rows where completed_date IS NULL.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

BACKFILL = """
UPDATE customer_order
SET completed_date = (
    SELECT date(customer_order.order_date,
                '+' || CAST(MAX(p.lead_time_days) AS INTEGER) || ' days')
    FROM customer_order_line l
    JOIN part p ON p.part_id = l.part_id
    WHERE l.order_id = customer_order.order_id
      AND p.lead_time_days > 0
)
WHERE status IN ('Shipped', 'Closed')
  AND completed_date IS NULL;
"""


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        cols = {row[1] for row in cur.execute("PRAGMA table_info(customer_order)")}
        if "completed_date" not in cols:
            cur.execute("ALTER TABLE customer_order ADD COLUMN completed_date DATE")
            print("Added column customer_order.completed_date")
        else:
            print("Column customer_order.completed_date already exists — skipping add")

        cur.execute(BACKFILL)
        print(f"Backfilled {cur.rowcount} Shipped/Closed orders")

        # Fail closed: every completed-status order must now carry a date.
        missing = cur.execute(
            "SELECT COUNT(*) FROM customer_order "
            "WHERE status IN ('Shipped','Closed') AND completed_date IS NULL"
        ).fetchone()[0]
        if missing:
            raise RuntimeError(
                f"{missing} Shipped/Closed orders still have no completed_date — "
                "aborting (no lines with positive lead_time_days?)"
            )

        # Sanity: non-completed statuses must stay NULL.
        stray = cur.execute(
            "SELECT COUNT(*) FROM customer_order "
            "WHERE status NOT IN ('Shipped','Closed') AND completed_date IS NOT NULL"
        ).fetchone()[0]
        if stray:
            raise RuntimeError(f"{stray} Open/Cancelled orders unexpectedly have a completed_date")

        conn.commit()

        for status, n, lo, hi in cur.execute(
            "SELECT status, COUNT(*), MIN(completed_date), MAX(completed_date) "
            "FROM customer_order GROUP BY status ORDER BY status"
        ):
            print(f"  {status:<10} {n:>3} orders  completed_date range: {lo} .. {hi}")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
