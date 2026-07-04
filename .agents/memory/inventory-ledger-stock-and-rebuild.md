---
name: Inventory ledger stock & rebuild seeding
description: How to derive on-hand stock from inventory_transaction, and why stock literals must be baked (not computed at seed time).
---

# Inventory ledger stock & rebuild seeding

## Ledger sign convention
`inventory_transaction.quantity` is **unsigned**; direction lives in `inventory_transaction.type`:
- `type='I'` = receipt (adds to stock)
- `type='O'` = issue (subtracts from stock)

Current on-hand = `SUM(CASE WHEN type='I' THEN quantity ELSE -quantity END)`, then **floored at 0**.

**Why:** `SUM(quantity)` is gross movement, not stock — it double-counts and ignores issues (e.g. one PN part read 84.2 gross vs 5.8 net). The synthetic ledger is unbalanced for some parts (issues > receipts, or issues with zero receipts), so raw net can go negative; a stockout must show as 0, never negative physical stock.

**How to apply:** whenever seeding/deriving `part.on_hand_qty` (or any stock figure) from the ledger, sign by `type` and floor at 0. Never `SUM(quantity)`.

## Rebuild path does NOT seed the ledger
The minimal rebuild (`hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`) runs only `add_purchasing_wip_tables.run()` after the schema — it does **not** seed `inventory_transaction` (that lives only in `scripts/seed_erp_synthetic.py`, a separate manual step).

**Why:** a seed function that computes stock from the ledger at seed time would get 0 for every part on a fresh rebuild (no ledger rows present).

**How to apply:** bake ledger-derived stock as **literals** in the seed (deterministic, zero ordering dependency), and re-verify those literals against the live ledger only in the one-shot backfill migration (which runs against the fully-seeded committed DB), guarding the check to parts that actually have ledger rows.
