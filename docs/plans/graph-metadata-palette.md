# Graph Metadata Palette

## What & Why
The private repo (Windows / SQL Server) has a `get_production_data(query: str) -> pd.DataFrame`
pattern — a reusable connection function that takes raw SQL and returns a DataFrame. The
`replit_integrations/` folder in the private repo is already set up to receive the matching
integration point from this public repo.

This task builds the public-repo counterpart: `get_graph_metadata(query: str) -> pd.DataFrame`
— a clean, reusable SQLite connection template that callers pass any graph metadata SQL query to
and get back a DataFrame. It is the prototype that informs the private repo's
`9004 Graph Metadata Palette.md` documentation.

Key metadata tables the function will be documented against:
- `schema_concepts`, `schema_perspectives`, `schema_intents`
- `schema_intent_concepts`, `schema_intent_perspectives`, `schema_concept_fields`
- `schema_perspective_concepts`, `schema_intent_queries`
- `schema_nodes`, `schema_edges`, `schema_topology_metadata`

## Done looks like
- New module `hf-space-inventory-sqlgen/scripts/get_graph_metadata.py` with:
  - `get_connection(db_path=None) -> sqlite3.Connection` — connection factory,
    defaults to manufacturing.db via env var or relative path
  - `get_graph_metadata(query: str, params=None, db_path=None) -> pd.DataFrame` —
    executes the query and returns a DataFrame; handles connection open/close,
    raises clear errors on failure
  - `if __name__ == "__main__"` demo block that runs a sample query and prints
    the first 5 rows — confirms the module works standalone
- A test file `tests/test_get_graph_metadata.py` that:
  - Calls `get_graph_metadata()` with a simple `SELECT` against each major metadata
    table and asserts the result is a non-empty DataFrame with expected columns
  - Tests error handling (bad SQL raises, not silently returns empty)
- `post-merge.sh` wired to run the new test file
- `graph_sync.py` `_load_sqlite_data()` is **not** changed in this task —
  refactor is out of scope; this task is additive only

## Out of scope
- Refactoring existing `_load_sqlite_data()` or `solder_engine.py` (additive only)
- ArangoDB queries (SQLite only)
- Perspective / intent mapping cleanup
- Private repo implementation (this is the prototype; private repo ports it separately)

## Steps
1. **Write `get_connection()`** — Connection factory for manufacturing.db. Reads
   `SQLITE_DB_PATH` env var with fallback to the relative path. Enables WAL mode and
   `row_factory = sqlite3.Row`.
2. **Write `get_graph_metadata(query, params, db_path)`** — Opens connection via
   `get_connection()`, runs `pd.read_sql_query(query, conn, params=params)`, closes
   connection, returns DataFrame. Raises `ValueError` on empty query; wraps
   `sqlite3.OperationalError` with a clear message.
3. **Write demo `__main__` block** — Runs one sample query per major table group
   (intents, concepts, perspectives) and prints shape + head.
4. **Write tests** — One test per major metadata table asserting non-empty DataFrame
   and correct column names. One test for bad SQL raising an exception.
5. **Wire post-merge.sh** — Add the new test file to the run list.

## Relevant files
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `scripts/post-merge.sh`
