# WIP Relief on Work-Order Close

## What & Why
Complete the cost cycle: when a work order is closed, relieve its accumulated WIP into Finished Goods (or COGS for make-to-order shipments — keep it simple: Finished Goods only), dated at the WO's `close_date`. This makes the GL tell the full manufacturing story: costs flow into WIP during production and out at close.

## Done looks like
- Deterministic, idempotent migration posts one relief entry per **closed** work order: credit the WIP accounts for the WO's full accumulated cost by element (labor, burden, material, service), debit Finished Goods for the total.
- Relief amounts equal the sum of that WO's WIP postings from the prior posting migrations — computed from the GL itself, not re-derived from source tables — so the ledger is internally consistent by construction.
- After relief, WIP balance per closed WO is exactly zero; migration fails closed if any closed WO retains a WIP balance or any open WO gets relieved.
- Open/unreleased/firmed WOs (including WO-PLN-* planned orders) are never touched.
- Wired into the bootstrap chain after the two posting migrations.

## Out of scope
- Variance accounts (standard vs actual) — everything relieves at actual.
- COGS / shipment postings.

## Steps
1. **Relief rules** — per-element WIP credit + Finished Goods debit at close_date; explicitly exclude non-closed statuses and planned orders.
2. **Migration script** — compute per-WO WIP balances from gl_transaction, post relief entries with idempotency keys, wire into bootstrap chain.
3. **Zero-balance gate** — assert closed-WO WIP nets to zero and open-WO WIP is untouched; fail closed with named offenders.

## Relevant files
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
