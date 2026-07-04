---
title: MRP Demand-Supply Schedule Grid
---
# MRP Demand-Supply Schedule Grid

## What & Why
Add a dedicated Gradio tab that presents a time-phased MRP demand-supply schedule for the synthetic manufacturing data: monthly buckets across a rolling horizon that net open demand against on-hand inventory and existing work-order/purchase-order supply, and suggest planned orders across the next 6 months. This gives planners the classic MRP planning grid, inspired by the real-source `ufn_demand_supply` benchmark but as a forward-looking time-phased view rather than order-level pegging.

## Done looks like
- A new tab shows an MRP grid for a selected part with monthly bucket columns and rows for: Gross Requirements, Scheduled Receipts, Projected Available Balance, Net Requirements, Planned Order Receipts, and Planned Order Releases.
- Planned orders are generated across a 6-month forward horizon and released earlier by each part's lead time (release date = need date − lead time).
- Open customer-order demand lands in the correct month via a derived need-by date on each line; existing work orders and purchase orders appear as scheduled receipts in their due months.
- The grid header clearly shows the as-of anchor date and the horizon; every number is deterministic and computed read-only against SQLite.
- Missing planning inputs (e.g., a part with no lead time, or unresolved supply) fail with a clear message rather than silently defaulting to zero.

## Out of scope
- Peg-level demand-supply-link allocation (linking specific work orders to specific customer orders) — deferred; needs more design/PM input.
- Multi-level BOM explosion / dependent-demand cascade beyond single-level part netting (v1 nets independent customer-order demand per part).
- Any writes to the live/production database or ArangoDB, and any non-SQLite dialect (SQLite synthetic target only).

## Key design constraints
- **Data-derived as-of anchor, never wall-clock.** Existing synthetic dates end ~mid-2026, so anchor the horizon to a date derived from the data (consistent with the project's operation-progress backfill convention) and derive demand need-by dates forward from it.
- **Deterministic synthetic data only** (no random per-run values); SQLite is the synthetic target dialect.
- **Fail closed** on missing/ambiguous planning inputs (explicit error over silent fallback).
- Keep the seed schema in sync with any new columns so a database rebuild reproduces them (don't only mutate the live DB).

## Steps
1. **Derive demand timing (synthetic data)** — Add a need-by date to each open customer-order line plus a desired-release date equal to need-by minus the part's lead time, spread deterministically across the forward horizon from a data-derived as-of anchor so open demand populates the monthly buckets. Sync the seed schema.
2. **Enrich supply attributes (synthetic data)** — Add a service date and vendor to outside-service work orders, and ensure purchased components (BUY / RAW / hardware / outside-service) have open purchase-order receipts landing in the horizon, so scheduled receipts are realistic. Sync the seed schema.
3. **Build the MRP netting engine** — Compute, per part and per monthly bucket over the horizon, the standard grid lines (gross requirements, scheduled receipts, projected available balance, net requirements, planned order receipts, planned order releases) using full netting and lead-time-offset planned orders, anchored to the data-derived as-of date, failing closed on missing inputs.
4. **Add the dedicated Gradio tab** — Present the time-phased grid with monthly bucket columns and the MRP rows, a part (and part-class) selector, and a visible as-of/horizon header, reading read-only from SQLite.
5. **Tests + gate** — Add deterministic tests covering the netting math, lead-time offset, data-derived anchor (not wall-clock), monthly bucket boundaries, and fail-closed behavior; wire them into the existing test gate.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:4417-4456`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/scripts/seed_erp_synthetic.py`
- `hf-space-inventory-sqlgen/migrations/backfill_operation_schedule.py`
- `hf-space-inventory-sqlgen/migrations/regap_and_seed_requirements.py`
- `hf-space-inventory-sqlgen/migrations/relabel_work_order_status.py`
- `Data_Models/Customer_Order/Demand and Supply 1 fn.sql`
- `hf-space-inventory-sqlgen/tests/`
- `scripts/post-merge.sh`