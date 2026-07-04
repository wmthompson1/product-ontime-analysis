"""
Migration: fold the orphaned PN-* namespace into the parts master + planner.

Problem repaired
----------------
50 work orders (and the po_line / material_issue rows that reference them) point
at 20 PN-* part numbers that were never inserted into the `part` master, so
`work_order.part_id` had 20 phantom values with no item-master row. All parts on
a work order must exist in the master (obsolete/inactive is fine, absent is not).

What this does (idempotent, SQLite-only synthetic)
--------------------------------------------------
  - Adds the native item-master column `part.planner_code` if missing.
  - Seeds the 20 PN-* parts into the master as planned, fabricated items
    (part_class MAKE — their work orders / routings are retained per the planning
    decision), with on_hand_qty baked from the inventory_transaction ledger NET
    (receipts type 'I' minus issues type 'O'), floored at 0 so a stockout shows
    as zero rather than negative physical stock. Also converges the stock fields
    on rows an earlier run may have baked differently.
  - Assigns a generic owning planner (planner_code = 'ENGINEERING') to every part.
  - Re-verifies each seeded on_hand_qty against the live ledger net (grounding).

The seeding logic itself lives in add_purchasing_wip_tables.seed_pn_parts_master
(the module that owns the PN-* namespace) so the fresh-rebuild seed path and this
one-shot patch of the committed DB stay in lockstep. Safe to re-run.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/backfill_pn_parts_master_and_planner.py
"""

import os
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from add_purchasing_wip_tables import seed_pn_parts_master  # noqa: E402

DB_PATH = os.path.join(_HERE, "..", "app_schema", "manufacturing.db")


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    seed_pn_parts_master(cur)
    conn.commit()

    orphans = cur.execute(
        "SELECT COUNT(*) FROM work_order "
        "WHERE part_id NOT IN (SELECT part_id FROM part)"
    ).fetchone()[0]
    pn_master = cur.execute(
        "SELECT COUNT(*) FROM part WHERE part_id LIKE 'PN-%'"
    ).fetchone()[0]
    no_planner = cur.execute(
        "SELECT COUNT(*) FROM part WHERE planner_code IS NULL OR planner_code=''"
    ).fetchone()[0]
    wo_missing_ops = cur.execute(
        "SELECT COUNT(*) FROM work_order wo WHERE wo.part_id LIKE 'PN-%' "
        "AND NOT EXISTS (SELECT 1 FROM operation o WHERE o.wo_id = wo.wo_id)"
    ).fetchone()[0]

    # Grounding: every seeded PN on_hand must equal the live ledger net
    # (receipts type 'I' minus issues type 'O', floored at 0). Only checked for
    # parts that actually have ledger rows, since the minimal rebuild path seeds
    # no inventory_transaction data.
    ledger_net = {
        pid: round(max(net, 0.0), 1)
        for pid, net in cur.execute(
            "SELECT part_id, "
            "SUM(CASE WHEN type='I' THEN quantity ELSE -quantity END) "
            "FROM inventory_transaction WHERE part_id LIKE 'PN-%' "
            "GROUP BY part_id"
        ).fetchall()
    }
    on_hand_mismatch = []
    for pid, seeded in cur.execute(
        "SELECT part_id, on_hand_qty FROM part WHERE part_id LIKE 'PN-%'"
    ).fetchall():
        if pid in ledger_net and round(seeded, 1) != ledger_net[pid]:
            on_hand_mismatch.append((pid, seeded, ledger_net[pid]))

    # Collapse the WAL so the committed main DB file (read by the graph exporter)
    # reflects these writes.
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.commit()
    conn.close()

    print(f"  orphaned work-order parts remaining: {orphans}")
    print(f"  PN-* parts in master:                {pn_master}")
    print(f"  parts missing planner_code:          {no_planner}")
    print(f"  PN-* work orders missing operations: {wo_missing_ops}")
    print(f"  PN-* on_hand vs ledger-net mismatch: {len(on_hand_mismatch)}")

    assert orphans == 0, "referential integrity: every WO part must be in master"
    assert pn_master == 20, f"expected 20 PN-* master rows, got {pn_master}"
    assert no_planner == 0, "every part must have a planner_code"
    assert not on_hand_mismatch, (
        "seeded on_hand must equal ledger net (floored at 0); "
        f"mismatches: {on_hand_mismatch}"
    )
    print("Done. PN-* namespace folded into the parts master; planners assigned.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
