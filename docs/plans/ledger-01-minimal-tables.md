# Minimal Synthetic GL Ledger Tables

## What & Why
Create the minimal, deterministic ledger tables for the synthetic GL — no control logic, no reconciliation machinery. Per the PM plan: `gl_raw_materials_inventory`, `gl_wip_inventory`, `gl_finished_goods_inventory`, `gl_job_cost_detail`, and `gl_events`. Each table stays lightweight: id, job_id, amount, timestamp, event_type (plus part/source linkage where it costs nothing).

## Done looks like
- An idempotent migration (`CREATE TABLE IF NOT EXISTS`, safe re-run) creates the five tables in the SQLite twin (`manufacturing.db`).
- `job_id` is the existing `work_order.wo_id` (structural FK declared; enforcement is off, so declaration is for graph derivation only).
- Timestamps are data-derived from source documents, never wall-clock.
- The migration is wired into the bootstrap chain (`rebuild_clean_db.py`) so a fresh clone gets the tables; verified via `sqlite3` dumps (DB is WAL-mode and gitignored).
- No period-close, control-account, or validation columns — deliberately minimal.

## Out of scope
- Posting functions and data population (Task 2).
- Ontology/graph registration (later tasks).

## Steps
1. **DDL design** — five minimal tables with the shared column shape and wo_id linkage; document the shape in the migration docstring.
2. **Migration script** — idempotent DDL, added to the bootstrap execution chain.
3. **Verification** — self-check that tables exist and re-run is a no-op.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
