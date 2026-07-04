# Plan-010: Graph-to-Solder Catalog Exporter

## What & Why
The ArangoDB `contains` edge collection holds the certified structural topology of the manufacturing schema (table → column containment edges). The Solder Engine holds all approved SQL snippets. Right now there is no direct link between them — an approved SQL binding could silently reference a table or column that no longer exists in the certified graph.

Plan-010 closes that gap by introducing a single Python script that:
1. **Exports** the graph topology to a flat column-catalog JSON (one entry per column, resolved via AQL `DOCUMENT()` projection).
2. **Validates** every approved SolderEngine binding against that catalog, asserting that all table references in approved SQL exist in the graph-certified schema.

The output JSON can also serve as a stable fixture for the test suite, replacing any ad-hoc schema assumptions in future Solder validation tests.

## Done looks like
- `hf-space-inventory-sqlgen/scripts/export_graph_to_solder.py` exists and runs standalone (`python export_graph_to_solder.py`).
- Running it with no flags prints a JSON array to stdout, one entry per column, with fields: `qualified_name` (e.g. `"PRODUCTION_SCHEDULE.line_id"`), `table_name`, `column_name`, `data_type`, `primary_key` (bool), `not_null` (bool).
- Running with `--output <path>` writes the JSON array to a file (default: `solder_catalog.json` next to the script).
- Running with `--validate` additionally loads all approved SolderEngine bindings via `load_approved_bindings()`, extracts table references from each binding's SQL using `_extract_tables_from_sql()`, and reports any table name present in an approved binding that is absent from the graph catalog. Exit code is 0 when all approved bindings are catalog-clean, non-zero otherwise.
- Running with `--dry-run` prints what would be written without touching the file system.
- A new test file `hf-space-inventory-sqlgen/tests/test_solder_graph_catalog.py` imports `export_graph_to_solder` and has at least two tests: one that confirms the catalog contains at least one row for each table in `schema_nodes`, and one that calls `--validate` logic and asserts no approved binding references a table outside the graph catalog. Both tests skip gracefully when ArangoDB env vars are absent (matching the pattern in `test_bridge_collection_health.py`).

## Out of scope
- Writing the catalog back to SQLite or `dab_config.json` — those paths are handled by plan-009 scripts.
- Validating individual column-level references (only table-level coverage is in scope here — column-level can be a follow-up).
- A Gradio UI trigger for the exporter — CLI + test only.
- Integrating this into the nightly GitHub Actions sync — can be added separately.

## Steps
1. **Write the AQL projection function** — Inside `export_graph_to_solder.py`, implement `fetch_solder_catalog(db)` that runs an AQL query over the `contains` edge collection using `DOCUMENT(e._from)` and `DOCUMENT(e._to)` to resolve table and column vertices. Map each result to `{qualified_name, table_name, column_name, data_type, primary_key, not_null}` using the field names already present on the ArangoDB vertices (`table_name`, `column_name`, `data_type`, `pk`, `not_null`). Return the list.

2. **Wire ArangoDB connection** — Reuse `get_arango_client` / `get_arango_db` / `GRAPH_NAME` patterns from `graph_sync.py`. Read `ARANGO_HOST`, `ARANGO_USER`, `ARANGO_ROOT_PASSWORD`, `ARANGO_DB` env vars. Exit with a clear error message (non-zero) when connection fails.

3. **Add `--output` and `--dry-run` CLI flags** — Use `argparse`. `--output` defaults to `solder_catalog.json` in the same directory as the script. `--dry-run` prints the catalog to stdout without writing. Print a summary line: `Exported N columns across M tables`.

4. **Add `--validate` mode** — Import `SolderEngine` from `solder_engine` (add `hf-space-inventory-sqlgen` to `sys.path` if running from `scripts/`). Call `load_approved_bindings()`, then for each binding call `_extract_tables_from_sql()` on its SQL text. Cross-reference the resulting table names against the catalog. Print a report: `All N bindings catalog-clean` or list the offending bindings with the unknown table names. Exit non-zero if any mismatches found.

5. **Write `tests/test_solder_graph_catalog.py`** — Two tests: (a) `test_catalog_covers_schema_nodes` — calls `fetch_solder_catalog()`, queries SQLite `schema_nodes` for table names, asserts every schema node appears in the catalog at least once; (b) `test_approved_bindings_are_catalog_clean` — runs the `--validate` logic and asserts zero mismatches. Both skip when `ARANGO_HOST` is not set, using `pytest.importorskip` / `pytest.mark.skipif` consistent with `test_bridge_collection_health.py`.

## Relevant files
- `hf-space-inventory-sqlgen/graph_sync.py:43-75`
- `hf-space-inventory-sqlgen/graph_sync.py:164-200`
- `hf-space-inventory-sqlgen/graph_sync.py:319-340`
- `hf-space-inventory-sqlgen/solder_engine.py:39-130`
- `hf-space-inventory-sqlgen/solder_engine.py:699-760`
- `hf-space-inventory-sqlgen/tests/test_bridge_collection_health.py`
- `hf-space-inventory-sqlgen/scripts/`
