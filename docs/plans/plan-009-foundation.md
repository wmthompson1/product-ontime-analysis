# Plan-009 Foundation: SQLite Metadata Tables

## What & Why
Waves 1–5 of plan-009 are implemented in a parallel private repo but have not yet landed in this Replit codebase. This task backports that work: three metadata tables in SQLite become the persistent source of truth for DAB field definitions and graph topology annotations, replacing direct reads from `dab_config.json`.

The principle: `dab-config.json` is a **sqlite-synced artifact**, not a source of truth. SQLite is.

## Done looks like
- `schema_sqlite.sql` contains `CREATE TABLE IF NOT EXISTS` blocks for `api_field_descriptions`, `schema_topology_metadata`, and `dab_field_definitions` (matching the DDL in the plan-009 reference doc exactly — composite primary keys, `certified` INTEGER 0/1, CHECK constraints on `source_node_type`/`target_node_type`).
- `init_sqlite_db()` in `app.py` calls a new `ensure_app_metadata_tables(conn)` function immediately after `executescript()`. That function handles legacy-schema migration for `api_field_descriptions` (rename → recreate → migrate → drop) and issues additive `CREATE TABLE IF NOT EXISTS` guards for all three tables.
- `APP_METADATA_TABLES = {"api_field_descriptions", "schema_topology_metadata", "dab_field_definitions"}` is defined near the top of `app.py` and `get_all_tables()` filters that set out of the `PRAGMA table_list` result.
- `save_field_description()` and `save_dab_field_definition()` write to their respective tables via `ON CONFLICT DO UPDATE`, keyed on `(source_database, schema_name, table_name, column_name)`. Both validate the column exists in the structural schema before writing.
- `get_unified_schema()` loads `STRUCTURAL_SCHEMA_SNAPSHOT` as the immutable base, then overlays `api_field_descriptions` rows (display_name, description, example_value) and `dab_field_definitions` rows (field_definition, certified) per column. Non-matching rows are silently skipped.
- The Gradio "Entity Field Descriptions" tab (currently reading directly from `dab_config.json` at line 4673/4687) is updated to read from `get_unified_schema()` / SQLite instead. `dab_config.json` remains on disk as a legacy reference until the sync script (wave 6) writes to it.

## Out of scope
- The consumer scripts (`sync_db_to_dab_config.py`, `reconstruct_containment_graph.py`) — those are wave 6, planned separately.
- A new Gradio form UI for editing field descriptions or DAB definitions — the write paths are wired but a full editor tab is not required here.
- `column_bindings` table changes — managed separately; additive creation guard is sufficient.

## Steps
1. **Add three metadata table DDL to `schema_sqlite.sql`** — Append `CREATE TABLE IF NOT EXISTS` blocks for `api_field_descriptions`, `schema_topology_metadata`, and `dab_field_definitions` exactly as specified in the plan-009 reference DDL. Use `IF NOT EXISTS` so the file is idempotent.

2. **Implement `ensure_app_metadata_tables(conn)`** — Add this function in `app.py` above `init_sqlite_db`. It must handle the two concerns: (a) legacy migration — detect a mismatched `api_field_descriptions` column set, rename to `_legacy`, recreate, migrate rows using `SQL_MCP_SOURCE_DATABASE` and `SQL_MCP_DEFAULT_SCHEMA` env defaults, drop legacy; (b) additive `CREATE TABLE IF NOT EXISTS` for all three tables and `column_bindings`. Call it from `init_sqlite_db` after `executescript`.

3. **Add `APP_METADATA_TABLES` constant and filter `get_all_tables()`** — Define the set near the top constants block in `app.py`. Update `get_all_tables()` to exclude those names from the `PRAGMA table_list` result.

4. **Implement dual metadata write/read paths** — Add `save_field_description()`, `get_field_description_record()`, `save_dab_field_definition()`, and `get_dab_field_definition_record()` in `app.py`. Write paths use `ON CONFLICT DO UPDATE`; both validate against the structural schema before writing.

5. **Implement `get_unified_schema()`** — Add the merge function in `app.py`. Load the structural snapshot, overlay `api_field_descriptions` rows, then overlay `dab_field_definitions` rows. Return the enriched column dict; silently skip orphaned rows.

6. **Migrate the Gradio field descriptions tab to SQLite** — Replace the direct `dab_config.json` file reads in the Entity Field Descriptions Gradio tab (around line 4673) with calls to `get_unified_schema()` or `get_field_description_record()`.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/app.py:59-95`
- `hf-space-inventory-sqlgen/app.py:163-175`
- `hf-space-inventory-sqlgen/app.py:2444-2483`
- `hf-space-inventory-sqlgen/app.py:4645-4700`
- `hf-space-inventory-sqlgen/dab_config.json`
