"""Add the physical `received_date` column to the `receiving` table.

The private-repo ground truth filters uninvoiced-receipt / delivery windows on
``R.RECEIVED_DATE`` — the date goods physically arrived at the dock — which is a
DISTINCT noun from ``receipt_date`` (the date the receipt transaction was
posted). The synthetic twin previously carried only ``receipt_date``, so the
governed Uninvoiced Receipts view had to alias the posting date as
``received_date``. The Temporal Parameter Contract binds its Horizon Filter to
the real ``received_date`` column, so that column must exist as a first-class
field, not an alias.

This migration is idempotent and deterministic:

  1. ADD COLUMN receiving.received_date DATE (nullable) if it is not present.
  2. Backfill received_date = receipt_date for every row still NULL.

In the synthetic twin the two dates coincide (goods arrived and were posted the
same day); they are modeled as separate fields because they are separate
business events and may diverge in the real source. Nothing about the twin's
existing results changes — receipt_date is left untouched, and the backfilled
received_date equals it row-for-row.

Run: python hf-space-inventory-sqlgen/migrations/add_received_date.py
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema",
                       "manufacturing.db")


def _has_column(cur, table, column):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not _has_column(cur, "receiving", "received_date"):
        cur.execute("ALTER TABLE receiving ADD COLUMN received_date DATE")
        print("  + receiving.received_date column added")
    else:
        print("  = receiving.received_date already present (idempotent)")

    cur.execute(
        "UPDATE receiving SET received_date = receipt_date "
        "WHERE received_date IS NULL")
    if cur.rowcount:
        print(f"  ~ backfilled received_date = receipt_date for "
              f"{cur.rowcount} row(s)")
    else:
        print("  = no NULL received_date rows to backfill")

    conn.commit()

    # FAIL-CLOSED VERIFY: no receiving row may be left without a received_date.
    missing = cur.execute(
        "SELECT COUNT(*) FROM receiving WHERE received_date IS NULL"
    ).fetchone()[0]
    if missing:
        raise SystemExit(
            f"FAIL: {missing} receiving row(s) still have NULL received_date")
    print("  VERIFY OK: every receiving row carries a received_date")
    conn.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
