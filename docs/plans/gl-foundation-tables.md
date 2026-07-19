# GL Foundation Tables & Chart of Accounts

## What & Why
Create the physical general-ledger tables the database currently lacks: a chart of accounts and a journal/transaction ledger. The `General_Ledger` perspective already exists in `schema_perspectives` but has no tables behind it. This is the foundation every posting task builds on.

## Done looks like
- A migration creates `account` (chart of accounts) and `gl_transaction` (journal lines) tables in the SQLite twin, idempotently (`CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`).
- A lean, manufacturing-focused chart of accounts is seeded deterministically: WIP (labor, material, burden, outside service), Raw Material Inventory, Finished Goods, COGS, Payroll Expense/Accrued Labor, Purchases/Received-Not-Invoiced — **no control accounts** and no subledger-control reconciliation, per the simplified synthetic design.
- `gl_transaction` rows carry: account, debit/credit amount (or signed amount — pick one convention and document it), posting date, source document type + id (labor_ticket, material_issue, receiving, payables, work_order), and wo_id/po_id/part_id linkage columns where applicable.
- The migration is wired into the bootstrap chain (`rebuild_clean_db.py`) so a fresh clone gets the tables.
- Declared FKs are structural-only (FK enforcement is off in this DB) — declare them for graph derivation even if seeding order would orphan.

## Out of scope
- Actual posting of transactions (separate tasks).
- Ontology/graph registration (separate task).
- Multi-currency, periods/fiscal calendar, account hierarchies.

## Steps
1. **Design the two tables** — chart-of-accounts table and journal-line table with source-document linkage columns; document the debit/credit vs signed-amount convention in the migration docstring.
2. **Migration script** — idempotent DDL + deterministic chart-of-accounts seed; add to the bootstrap execution chain.
3. **Verification** — migration self-check (tables exist, seed row counts, no duplicate account codes on re-run); verify via `sqlite3` dumps (DB is WAL-mode and gitignored).

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/migrations/add_wave4_traceability_tables.py`
