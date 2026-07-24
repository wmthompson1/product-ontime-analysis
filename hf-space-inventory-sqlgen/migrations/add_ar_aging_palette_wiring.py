"""Wire the AR Aging snippet into the Query Palette under the Receivables intent.

The receivables_araging_20260724_000001 snippet (AR aging bucketed by days
past due_date) is now approved in reviewer_manifest.json.  This migration
adds it as query_index=3 under intent 19 (order_revenue_recognition / Receivables
perspective) so it appears in the Query Palette when analysts drill into the
Receivables → OrderAccountingState chain.

What this migration does (deterministic, idempotent, fail-closed):

  1. Verifies intent 19 (order_revenue_recognition) is present; exits with a
     clear error if add_receivables_wiring.py has not been run first.
  2. Inserts the palette entry via INSERT OR IGNORE (safe to re-run).
  3. Verifies the row is present after the insert.

Run once (safe to re-run):
    cd hf-space-inventory-sqlgen
    python migrations/add_ar_aging_palette_wiring.py
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app_schema", "manufacturing.db"
)

BINDING_KEY = "receivables_araging_20260724_000001"

PALETTE_ENTRY = {
    "intent_id": 19,
    "query_category": "receivables",
    "query_file": BINDING_KEY,
    "query_index": 3,
    "query_name": "AR Aging — Open & Disputed Invoices",
}


def _fail(msg: str) -> None:
    raise SystemExit(f"[add_ar_aging_palette_wiring] FAIL-CLOSED: {msg}")


def run() -> None:
    print(f"DB: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    # 1 — verify intent 19 exists (add_receivables_wiring.py must have run)
    row = cur.execute(
        "SELECT intent_name FROM schema_intents WHERE intent_id = 19"
    ).fetchone()
    if not row:
        conn.close()
        _fail(
            "intent 19 (order_revenue_recognition) not found. "
            "Run migrations/add_receivables_wiring.py first."
        )
    print(f"  intent 19 found: {row[0]}")

    # 2 — insert palette entry (idempotent)
    cur.execute(
        """
        INSERT OR IGNORE INTO schema_intent_queries
            (intent_id, query_category, query_file, query_index, query_name)
        VALUES (:intent_id, :query_category, :query_file, :query_index, :query_name)
        """,
        PALETTE_ENTRY,
    )
    inserted = cur.rowcount
    print(
        f"  palette entry '{PALETTE_ENTRY['query_name']}': "
        f"{'inserted' if inserted else 'already present (skipped)'}"
    )

    conn.commit()

    # 3 — verify
    exists = cur.execute(
        "SELECT 1 FROM schema_intent_queries "
        "WHERE intent_id = 19 AND query_file = ?",
        (BINDING_KEY,),
    ).fetchone()
    if not exists:
        conn.close()
        _fail("palette entry not found after insert — something went wrong")

    conn.close()
    print(
        "\n[add_ar_aging_palette_wiring] done — "
        "AR Aging query wired to Receivables intent (intent 19, query_index 3)."
    )


if __name__ == "__main__":
    run()
