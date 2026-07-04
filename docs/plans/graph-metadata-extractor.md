# Graph Metadata Extractor

## What & Why
The private repo has a `get_production_data` pattern — a structured function that connects to the data source, pulls specific tables, and returns them in a clean format for downstream consumers (reporting, semantic routing, etc.).

The graph metadata lives in `manufacturing.db` SQLite tables (`schema_intents`, `schema_concepts`, `schema_perspectives`, `schema_intent_perspectives`, `schema_intent_concepts`, `schema_concept_fields`, `schema_perspective_concepts`, `schema_intent_queries`). Today there is no equivalent structured extractor — consumers reach into SQLite ad-hoc through `_load_sqlite_data()` in `graph_sync.py` or raw SQL in `solder_engine.py`.

This task builds `get_graph_metadata()` in this repo as the canonical prototype, mirroring the `get_production_data` contract from the private repo. Once proven here, it gets ported to the private repo where the same SQLite metadata tables will live alongside the SQL Server ERP data.

## Done looks like
- A new module `hf-space-inventory-sqlgen/scripts/get_graph_metadata.py` with a single public function `get_graph_metadata(db_path=None) -> dict`
- The function returns a dict with one key per semantic table — same structure that `_load_sqlite_data()` in `graph_sync.py` already returns, but callable standalone and importable
- A `--export` CLI flag writes the result to `graph_metadata.json` (pretty-printed, UTF-8) for use by the private repo
- `graph_sync.py` is refactored to call `get_graph_metadata()` instead of its inline `_load_sqlite_data()` — no behavior change, just deduplication
- `solder_engine.py` `_load_semantic_graph()` is updated to use `get_graph_metadata()` for the semantic tables it reads — no behavior change
- A test file `tests/test_get_graph_metadata.py` verifies the returned dict has the expected keys and that each value is a non-empty list when manufacturing.db is populated
- `post-merge.sh` runs the new test file
- Dry-run of `graph_sync.py` still passes cleanly after the refactor

## Out of scope
- Changing the SQLite schema or adding new tables
- Perspective/intent mapping cleanup (separate task)
- Private repo implementation (this is the prototype only)
- ArangoDB — this extractor is SQLite-only

## Steps
1. **Write `get_graph_metadata()`** — Extract the function body from `_load_sqlite_data()` in `graph_sync.py` into a new standalone module. Accept an optional `db_path` argument (defaults to the same env-var logic). Return the same dict structure.
2. **Add `--export` CLI** — When run as `python get_graph_metadata.py --export`, write `graph_metadata.json` to the working directory. Print a summary line (table name → row count) to stdout.
3. **Refactor `graph_sync.py`** — Replace the inline `_load_sqlite_data()` with an import of `get_graph_metadata`. Confirm dry-run still passes.
4. **Refactor `solder_engine.py`** — Replace the raw SQLite queries for semantic tables with calls to `get_graph_metadata()` where they overlap. Keep ERP-schema queries (tables, columns) separate — those are not graph metadata.
5. **Write tests** — Verify key presence, row counts > 0 on manufacturing.db, and that `--export` produces valid JSON.
6. **Wire into post-merge.sh** — Add the new test file to the post-merge run list.

## Relevant files
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `scripts/post-merge.sh`
