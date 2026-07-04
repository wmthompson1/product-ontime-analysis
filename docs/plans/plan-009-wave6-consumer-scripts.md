# Plan-009 Wave 6: DAB Sync & Containment Graph Reconstructor

## What & Why
With SQLite as the source of truth for field metadata and graph topology, two consumer scripts complete the pipeline:
- `sync_db_to_dab_config.py` — exports certified SQLite rows to `dab-config.json` as a point-in-time artifact.
- `reconstruct_containment_graph.py` — rebuilds ArangoDB `tables`, `columns`, and `contains` collections from `schema_topology_metadata` edge triples, so the graph always mirrors SQLite.

Both scripts are idempotent (re-run produces no net change when nothing has changed) and safe to call from CI or a cron job.

## Done looks like
- `hf-space-inventory-sqlgen/scripts/sync_db_to_dab_config.py` exists and can be run standalone (`python sync_db_to_dab_config.py`). It reads `dab_field_definitions WHERE certified = 1` for the active `SQL_MCP_SOURCE_DATABASE`, merges those `field_definition` values into the `entities[].fields[].description` array in `dab_config.json`, and writes the file back atomically (write-to-tmp, rename). Running it against an unchanged database produces no diff. The note at the top of `dab_config.json` is updated to reflect that the file is now generated from SQLite.
- `hf-space-inventory-sqlgen/scripts/reconstruct_containment_graph.py` exists and can be run standalone. It reads all rows from `schema_topology_metadata`, upserts `tables` and `columns` vertices into ArangoDB using the same key conventions as `graph_sync.py` (`_composite_key`, `table_vertex`, `column_vertex`), then upserts `contains` edges. It gracefully skips rows with unknown `edge_type` values and exits non-zero on ArangoDB connection failure so CI can detect it.
- Both scripts accept `--dry-run` to print what would change without writing.
- Both scripts print a brief summary on completion: counts of rows read, records written/skipped.

## Out of scope
- A Gradio UI trigger for either script — they are CLI-only in this task.
- GitHub Actions CI wiring for either script — can be added in a follow-up.
- Merging `reconstruct_containment_graph.py` into the existing `graph_sync.py` sync flow — it is a standalone recovery/bootstrap tool, not a replacement for the live sync watcher.

## Steps
1. **Write `sync_db_to_dab_config.py`** — Connect to `manufacturing.db`, query `dab_field_definitions WHERE certified = 1 AND source_database = $SQL_MCP_SOURCE_DATABASE`. For each row, locate the matching entity and field in the loaded `dab_config.json` dict and overwrite its `description` value with `field_definition`. Write the result atomically back to `dab_config.json`. Support `--dry-run` flag. Print a summary (rows read, fields updated, fields not matched).

2. **Write `reconstruct_containment_graph.py`** — Connect to `manufacturing.db` and ArangoDB (reuse the `get_arango_client` / `get_arango_db` / `ensure_graph` patterns from `graph_sync.py`). Read all rows from `schema_topology_metadata`. For each `(source_canonical_id, target_canonical_id, edge_type)` triple: upsert the source vertex into `tables` or `columns` per `source_node_type`, upsert the target vertex, then upsert the edge into the corresponding edge collection using `_upsert_edge`. Log skipped rows. Support `--dry-run`. Print a summary (vertices upserted, edges upserted, rows skipped).

3. **Wire both scripts to read env vars consistently** — Both scripts should respect `SQLITE_DB_PATH` (defaulting to the relative path `../app_schema/manufacturing.db` when called from the `scripts/` directory), `SQL_MCP_SOURCE_DATABASE`, `ARANGO_HOST`, `ARANGO_USER`, `ARANGO_ROOT_PASSWORD`, and `ARANGO_DB` — matching the conventions already in `graph_sync.py` and `app.py`.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/app.py:59-95`
- `hf-space-inventory-sqlgen/dab_config.json`
- `hf-space-inventory-sqlgen/graph_sync.py:43-75`
- `hf-space-inventory-sqlgen/graph_sync.py:164-210`
- `hf-space-inventory-sqlgen/graph_sync.py:319-340`
- `hf-space-inventory-sqlgen/scripts/`
