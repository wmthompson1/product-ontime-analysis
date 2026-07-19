# Post Procurement Flow to GL

## What & Why
Extend GL posting to the procurement side of the three-way match: material receipts post into Raw Material Inventory (offset: Received-Not-Invoiced), outside-service receipts post into WIP-Service for their linked work order, and matched payables clear Received-Not-Invoiced. Simplified: no AP control account — the payable posting's offset is a plain "Invoiced Purchases" style account, and no cash/payment leg is modeled.

## Done looks like
- Deterministic, idempotent migration posts entries from `receiving` (split material vs outside-service via the PO's `po_type`), and from matched `payables`/`payable_line` rows.
- Outside-service receipt postings tie to the correct work order via the existing (wo_id, service_id) linkage so WIP-Service per WO equals `work_order.act_ser_cost` for service sourced through POs; fail closed on drift.
- Received-not-invoiced balance in the GL equals the value of received-but-unmatched PO lines (the existing partial-receipt accrual concept), verifiable with one SQL query.
- Postings use data-derived dates (received_date, invoice dates), never wall-clock; fresh-clone bootstrap includes them.

## Out of scope
- Payment/cash postings, AP aging.
- Labor/material WIP postings and WO close relief (other tasks).

## Steps
1. **Posting rules** — account mapping per document type (material receipt, service receipt, matched invoice), honoring the simplified no-control design.
2. **Migration script** — generate journal lines from receiving and payables with idempotency keys; wire into the bootstrap chain after the WIP labor/material posting migration.
3. **Tie-out checks** — WIP-Service vs act_ser_cost per WO, and GL received-not-invoiced vs the partial-receipt accrual query; fail closed with named offenders.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/migrations/add_wave4_traceability_tables.py`
