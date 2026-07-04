# Drop Empty PoC Tables and Orphaned Metadata

## What & Why
The manufacturing.db contains ~21 empty tables that were created during early PoC development but never populated. They clutter the Schema Browser tab, inflate `schema_nodes` and `schema_intents` metadata, and cause the semantic layer to surface intents that can never resolve to real data. This work removes them cleanly — dropping the tables, retiring their Ground Truth SQL snippets, and pruning all referencing metadata.

## Done looks like
- All ~21 empty tables are gone from `manufacturing.db`
- Schema Browser shows only tables that have actual data
- `schema_nodes` contains no rows referencing the dropped tables
- All Ground Truth SQL snippets that JOIN against the dropped tables are removed or archived
- `schema_intents`, `schema_intent_queries`, and `ground_truth_table_usage` contain no dangling references
- `schema_sqlite.sql` seed script no longer creates the dropped tables or their metadata rows
- All 8 test files continue to pass (no broken references to dropped tables in tests)
- A migration script is committed so the change is reproducible (re-runnable against the deployed HF Space DB)

## Out of scope
- Populating any of the dropped tables with synthetic data (that is a separate decision)
- Changes to ArangoDB graph collections
- Trimming row counts in populated tables

## Steps

1. **Audit and categorise** — Enumerate all 21 empty tables into two groups: (a) fully orphaned (no GT SQL, no schema_nodes seed, no intents) and (b) referenced (have GT SQL snippets or schema metadata pointing at them). Produce a definitive list of each group before touching any files.

2. **Archive referenced Ground Truth SQL snippets** — Move any `.sql` files in the GT library that exclusively JOIN against dropped tables into an `_archived/` subfolder (do not delete, preserves git history). Update `ground_truth_table_usage` and `schema_intent_queries` to remove the dangling rows.

3. **Retire schema metadata rows** — Delete rows from `schema_nodes`, `schema_intents`, `schema_intent_queries`, `schema_perspective_concepts`, and `schema_concepts` that reference only the dropped tables. Rows that reference a mix of kept and dropped tables should be updated, not deleted.

4. **Write a forward migration script** — Create `hf-space-inventory-sqlgen/migrations/drop_poc_tables.py` that: drops each empty table with `DROP TABLE IF EXISTS`, deletes the associated `schema_nodes` rows, removes the dangling `schema_intents`/`schema_intent_queries` rows, and runs inside a transaction so it is atomic and re-runnable.

5. **Apply the migration to manufacturing.db** — Run `drop_poc_tables.py` against the local `manufacturing.db`. Verify with a quick `SELECT name FROM sqlite_master WHERE type='table'` that all target tables are gone.

6. **Update `schema_sqlite.sql`** — Remove the `CREATE TABLE` blocks and seed `INSERT` rows for all dropped tables so the DDL stays in sync with the live database and future re-seeds don't recreate the clutter.

7. **Fix any test references** — Scan test files for references to the dropped table names and update mocks or assertions. The `test_binding_key_hash.py` hashes may need regenerating if any archived GT snippets were previously included in the hash corpus.

8. **Smoke test** — Run `scripts/post-merge.sh` (all 8 test files) and confirm 8/8 pass. Also confirm the Schema Browser tab in the running app shows only the populated tables.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app.py`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/arangodb_helpers/manufacturing_graph_version_0_0_1.py`
- `hf-space-inventory-sqlgen/tests/test_binding_key_hash.py`
- `tests/test_structural_containment.py`
- `scripts/post-merge.sh`
