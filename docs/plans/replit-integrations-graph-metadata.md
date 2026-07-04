# replit_integrations — Graph Metadata Modules

## What & Why
The private repo (Windows / SQL Server) has its PYTHONPATH set to the cloned public
Replit repo's root (`SQL-Projects`). This means Python modules created here in a
`replit_integrations/` folder are directly importable in the private repo as:

    from replit_integrations.graph_metadata_queries import get_graph_metadata

The private repo already has prototype versions of two modules (✅ Step 1 done there).
This task creates the **canonical** versions here in the public repo — the source of
truth — following the same module-level function pattern as the existing
`hf-space-inventory-sqlgen/scripts/` files (`inspect_schema_intents.py`, `list_tables.py`).

Two modules are built in parallel:
- `graph_metadata_queries.py` — path resolver + SQLite connection wrapper
- `metadata_query_templates.py` — pre-built SQL query library (returns SQL strings)

Plus a demo script and documentation.

## Done looks like
- `replit_integrations/__init__.py` (empty, makes it a package)
- `replit_integrations/graph_metadata_queries.py` with:
  - `get_manufacturing_db_path() -> str` — path resolver (env var → relative fallback)
  - `get_graph_metadata(query: str, params=None, db_path=None) -> pd.DataFrame`
  - `close_connection()` — resource cleanup stub (connection-per-call pattern; no persistent state)
  - Error handling: missing DB raises `FileNotFoundError`; bad SQL raises `sqlite3.OperationalError` with message
  - Docstrings following existing scripts pattern
- `replit_integrations/metadata_query_templates.py` with SQL-returning functions:
  - Perspective: `list_perspectives()`, `perspective_concept_map()`, `perspective_intent_weights()`
  - Concept: `concept_hierarchy()`, `concept_field_mappings()`, `polymorphic_field_meanings(table_name, field_name)`
  - Intent: `intent_concept_elevations(intent_id)`, `intent_perspective_constraints(intent_id)`, `intent_query_mappings()`
  - Schema: `table_metadata()`, `column_metadata(table_name)`, `foreign_key_graph()`, `foreign_key_edges_from_table(table_name)`
  - Component: `polymorphic_components()`, `binding_key_resolution(component_id)`
  - Each returns a SQL string for use with `get_graph_metadata()`
- `replit_integrations/graph_metadata_demo.py` — runnable script:
  - Import verification (prints module paths)
  - Connection test to manufacturing.db
  - Five examples matching the plan: perspectives list, polymorphic field meanings, intent resolution, foreign key graph, ArangoDB _key format assertions (offline)
  - Expected output shown as inline comments
- `replit_integrations/replit_integrations.md` — updated with "Graph Metadata Extraction" section, import examples, troubleshooting
- Verification: `python replit_integrations/graph_metadata_demo.py` runs clean from the repo root with no import errors and prints DataFrame samples for each example

## Out of scope
- Synthetic ERP table data (separate task)
- `Utilities/SQLMesh/9004 Graph Metadata Palette.md` — private repo documentation, not created here
- ArangoDB live queries (offline _key format assertions only, as per approved decision)
- SQLMesh context (manufacturing.db is not a SQLMesh model — direct sqlite3 only)
- Changes to existing `hf-space-inventory-sqlgen/scripts/` files
- Adding to `post-merge.sh` (replit_integrations is an integration module, not part of the HF Space test suite)

## Steps
1. **Create package skeleton** — `replit_integrations/__init__.py` (empty). Confirms the folder is a Python package.
2. **Write `graph_metadata_queries.py`** — `get_manufacturing_db_path()` using `SQLITE_DB_PATH` env var with relative fallback to `hf-space-inventory-sqlgen/app_schema/manufacturing.db`. `get_graph_metadata()` opens connection per call via `pd.read_sql_query`, closes it, returns DataFrame. Direct `sqlite3` only — no SQLMesh dependency.
3. **Write `metadata_query_templates.py`** *(parallel with step 2)* — All SQL template functions listed above. Each returns a plain SQL string. No imports beyond stdlib. Keep queries consistent with actual SQLite schema columns (verify against `schema_sqlite.sql`).
4. **Write `graph_metadata_demo.py`** — Five named examples. Each calls a template function then `get_graph_metadata()` and prints `df.head()`. Include offline ArangoDB _key format assertion (`assert key.startswith("table::") or key.startswith("column::")`).
5. **Write `replit_integrations.md`** — Document module usage, import path, PYTHONPATH setup requirement, troubleshooting for SQLite path issues.
6. **Verify end-to-end** — Run `python replit_integrations/graph_metadata_demo.py` from repo root and confirm each example prints non-empty DataFrame output.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/scripts/inspect_schema_intents.py`
- `hf-space-inventory-sqlgen/scripts/list_tables.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
