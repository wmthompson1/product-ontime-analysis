# Schema tab: Payables table + hide internal tables

## What & Why
Two fixes to the Schema tab (Schema Browser):
1. **A real Payables table with dates.** The AP header table is currently named `invoice_header` (it already carries `invoice_date`, `due_date`, `payment_date`), while `payable_line` only has `created_at`. Rename `invoice_header` → `payables` so the schema shows a proper Payables table with its own dates, matching real ERP AP naming (payables header + payable_line detail). `payable_line.invoice_id` keeps pointing at the renamed header.
2. **Hide internal `schema_*` tables.** The table dropdown currently leaks 11 internal `schema_*` semantic-layer tables (schema_concepts, schema_edges, schema_intents, …). Filter all `schema_*`-prefixed tables out of the Schema Browser and everywhere else `get_all_tables()` feeds (ground-truth table list, structural snapshot), alongside the existing APP_METADATA_TABLES exclusions.

## Done looks like
- Schema tab dropdown shows `payables` (not `invoice_header`); its DDL shows invoice_date / due_date / payment_date.
- No `schema_*` tables appear in the Schema tab dropdown or "View All Tables" output.
- All parity gates and tests in `scripts/post-merge.sh` pass (except the known out-of-scope live-AQL check), and `bootstrap_db.py` rebuilds a fresh DB with the new name.

## Out of scope
- Renaming `payable_line` or its `invoice_id` column — column names stay as-is.
- Adding new date columns to `payable_line` (dates live on the payables header).
- Hiding other internal tables (`sql_graph_*`, `users`, `sqlite_sequence`, etc.) — only `schema_*` per the request; can be a follow-up if wanted.
- The known live-ArangoDB AQL parity failure (pre-existing).

## Steps
1. **DB migration** — New idempotent migration renaming `invoice_header` → `payables` (ALTER TABLE RENAME; SQLite auto-updates FK references). Wire it into the bootstrap migration chain. Verify via sqlite3 dumps (DB is WAL-mode and gitignored).
2. **Seed + schema sources** — Update the schema seed file (table def, schema_nodes/schema_edges rows, descriptions) so the startup INSERT OR IGNORE re-seed doesn't resurrect the old name.
3. **Code + queries sweep** — Update all live references to `invoice_header` (app code, solder engine fingerprints/bindings, saved queries and ground-truth snippets, seeder, prune script). Historical migrations stay untouched. Re-register any snippet fingerprints whose base tables change.
4. **Graph re-freeze** — Update `sql_graph_nodes` / `sql_graph_edges` (table node + column:: keys), re-serialize `graph_metadata.json` with a SCHEMA_VERSION bump, update `field_descriptions.csv` / `table_descriptions.csv` rows, and push to the live Arango graph via the canonical loader.
5. **Schema Browser filter** — Exclude `schema_*`-prefixed tables in the shared table-list helpers so the dropdown, All-Tables DDL, and structural snapshot all skip them.
6. **Verify** — Restart the app, confirm the dropdown contents via the Gradio API, and run the affected test files gate-style plus the parity checks (SQL↔file is the authoritative gate).

## Relevant files
- `hf-space-inventory-sqlgen/app.py:70-77`
- `hf-space-inventory-sqlgen/app.py:674-745`
- `hf-space-inventory-sqlgen/app.py:4482-4519`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/scripts/seed_erp_synthetic.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app_schema/queries/supplier_performance.sql`
- `hf-space-inventory-sqlgen/app_schema/queries/delivery_performance_perspectives.sql`
- `field_descriptions.csv`
- `table_descriptions.csv`
- `replit_integrations/sql_graph_parity_check.py`
- `scripts/post-merge.sh`
