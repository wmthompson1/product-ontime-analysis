---
title: Demand linkage + 3-month planning horizon extension
---
# Demand Linkage and Planning Horizon Extension

## What & Why
The synthetic ERP currently has zero demand lineage: every work order is an unlinked MO (the "no demand traceability" row of the order-type matrix). Per SME guidance, at least half of the orders should be demand-linked (Release Order → MO / Contract Order + MO patterns), and since unlinked orders ship from the order line, a forecast demand source should feed MRP for them. The planning schedule also needs to extend ~3 months further out with planned orders across the extended horizon, so the MRP grid shows a realistic forward plan.

## Done looks like
- At least half of the work orders are linked to a customer-order demand source (order line), with the linkage visible in the data and queryable.
- Unlinked-order parts that ship from the order line have forecast demand rows that MRP treats as gross requirements (alongside customer-order demand, without double-counting where a linked order already covers the demand).
- Synthetic demand and supply extend ~3 months beyond the current end (new need-by dates out to roughly July 2026), and the MRP grid plans orders across the extended horizon (planned receipts / planned releases appear in the later buckets).
- The MRP Schedule tab still renders correctly, fail-closed validation still passes (every in-horizon demand part has positive lead time and a real supply basis), and the existing test suite passes.
- The rebuild chain (`bootstrap_db.py`) reproduces all of this idempotently from a fresh clone.

## Out of scope
- Contract/Project module semantics (milestone invoicing, CDRLs) — linkage is a simple demand-source reference, not full contract costing.
- Repetitive/rate-based MO types and subcontract MO→PO chains.
- Any ontology/graph changes for the new linkage column(s) beyond what parity gates require.
- UI redesign of the MRP tab (only whatever small display additions the linkage/forecast needs, if any).

## Steps
1. **Demand linkage schema + backfill** — Add a demand-source link from work orders to customer order lines (nullable, structural FK per house style), then link at least half of the existing/open work orders to matching order lines (same part, compatible quantity/date), deterministically.
2. **Forecast demand source** — Add a forecast table (part, qty, forecast date, site) seeded for parts on unlinked orders that ship from the order line; extend MRP gross requirements to consume forecast alongside customer-order demand with a deterministic consumption rule so linked demand is not double-counted.
3. **Extend the planning schedule 3 months** — Extend synthetic demand (new customer-order lines and forecast rows) and supply context ~3 months past the current 2026-04-15 end; widen the MRP horizon (or bucket count) so the new months are visible, and confirm lot-for-lot planned receipts/releases populate the extended buckets.
4. **Seed + migration chain integration** — Fold the schema change, linkage backfill, and forecast seeding into the migration chain and `bootstrap_db.py` so a fresh rebuild reproduces the linked/unlinked mix and the extended horizon; keep everything deterministic (no wall-clock, data-derived AS_OF).
5. **Tests + gates** — Add/extend tests for the linkage ratio (≥50%), forecast-vs-order-demand netting, and extended-horizon planned orders; run the MRP validation and existing test files; verify the MRP Schedule and related tabs still serve correctly.

## Relevant files
- `hf-space-inventory-sqlgen/mrp_engine.py`
- `hf-space-inventory-sqlgen/migrations/backfill_mrp_demand_supply.py`
- `hf-space-inventory-sqlgen/migrations/regap_and_seed_requirements.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/tests/test_mrp_schedule.py`
- `hf-space-inventory-sqlgen/app.py`