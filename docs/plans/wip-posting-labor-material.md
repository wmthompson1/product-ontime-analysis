# Post Labor, Burden & Material to WIP

## What & Why
Populate the new GL journal with WIP postings derived from existing shop-floor activity: every `labor_ticket` posts labor + burden into WIP, every `material_issue` posts material into WIP. Simplified synthetic posting: each entry debits the relevant WIP account and credits a single offset account (Payroll/Accrued Labor for labor+burden, Raw Material Inventory for material) — no control accounts, no batch/period close.

## Done looks like
- A deterministic, idempotent migration posts one balanced journal entry per source row (labor_ticket → WIP-Labor + WIP-Burden, material_issue → WIP-Material), dated with data-derived dates from the source rows — never wall-clock.
- Re-running the migration creates no duplicate postings (keyed on source document type + id).
- Sum of WIP-Labor/Burden/Material postings per work order exactly equals `work_order.act_lab_cost` / `act_bur_cost` / `act_mat_cost` for orders whose costs come from these sources; migration fails closed on drift and reports the offending WOs.
- Fresh-clone bootstrap includes these postings.

## Out of scope
- Outside-service and procurement postings (separate task).
- WIP relief on work-order close (separate task).
- Any change to labor_ticket / material_issue / work_order cost columns.

## Steps
1. **Posting rules** — define the account mapping and entry shape per source type; document in the migration.
2. **Migration script** — deterministic generation of journal lines from labor_ticket and material_issue with idempotency keys; wire into the bootstrap chain after the GL foundation migration.
3. **Reconciliation check** — per-WO tie-out of posted WIP vs work_order actual cost columns, fail closed on mismatch (mirror the existing labor-chain reconciliation approach).

## Relevant files
- `hf-space-inventory-sqlgen/migrations/backfill_labor_chain.py`
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
