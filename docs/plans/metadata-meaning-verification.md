# Metadata Meaning Verification — Two-Sweep Script

## What & Why
Today there is no single script that proves the semantic graph and the physical SQLite schema are telling the same story end-to-end. A validation gap exists between:
- the ArangoDB ELEVATES edges (meaning layer), and
- the PRAGMA table_info column attributes in SQLite (physical layer).

This task creates `scripts/verify_metadata_meaning.py` — a standalone two-sweep validation script — by composing the building blocks that already exist: `replit_integrations/metadata_query_templates.py` (semantic SQL templates including `intent_concept_elevations`) and `replit_integrations/graph_metadata_queries.py` (`get_table_columns`, `get_all_table_names`). The reviewer manifest in `solder_engine.py` provides the approved-binding lookup. No new modules need to be created; only the script itself and its CI hook are new.

## Done looks like
- `scripts/verify_metadata_meaning.py` exists and is runnable standalone
- **Sweep 1 — Intent-Driven Semantic Triple Benchmark** passes when run:
  - The script reads live ELEVATES edges from ArangoDB (e.g. `intent::Payables_Audit → elevates → concept::AccruedLiabilities`)
  - It reconstructs the semantic triple explicitly: Subject (intent vertex), Predicate (ELEVATES), Object (concept vertex)
  - It cross-checks the concept_anchor against APPROVED bindings in the SQLite reviewer manifest (via `SolderEngine.load_approved_bindings()`)
  - It prints a PASS/FAIL row per triple with the resolved SQL snippet path; the script exits non-zero if zero triples could be checked
- **Sweep 2 — AQL-to-SQLite Column Parity Matrix** passes when run:
  - The script fetches all `columns` vertex keys from ArangoDB (format: `column::TABLE.COLUMN`)
  - For each key it parses TABLE and COLUMN, then calls `graph_metadata_queries.get_table_columns(table)` to look up that column in SQLite
  - It prints a matrix: `ArangoDB Key | data_type | pk | notnull | status` where status is MATCH, MISSING_IN_SQLITE, or TABLE_NOT_FOUND
  - The script exits non-zero if any column key resolves to MISSING_IN_SQLITE (hard failure gate)
- The script skips gracefully (exit 0, prints SKIP) when ArangoDB env vars are absent — same pattern as `tests/test_bridge_collection_health.py`
- The script is added as a step in `scripts/post-merge.sh` after the existing 8 test files

## Out of scope
- Changes to any Gradio tab UI
- Changes to the nightly GitHub Actions sync workflow
- New ArangoDB edges or SQLite schema changes
- Modifying `solder_engine.py`, `graph_sync.py`, or any existing module in `replit_integrations/`

## Steps
1. **Sweep 1 — Semantic Triple Benchmark** — In `scripts/verify_metadata_meaning.py`, connect to ArangoDB using the same env-var pattern as `graph_sync.py`. Query the `elevates` edge collection for all ELEVATES edges. For each edge, retrieve the source intent vertex and target concept vertex. Cross-check each concept's name against `SolderEngine.load_approved_bindings()` concept_anchor values. Print a structured PASS/FAIL table. Exit non-zero if zero triples were checked (empty graph guard).

2. **Sweep 2 — AQL-to-SQLite Column Parity Matrix** — In the same script, query all documents in the `columns` vertex collection. Parse each `_key` using the `column::TABLE.COLUMN` convention (helper already in `arangodb_helpers/manufacturing_graph_version_0_0_1.py`). For each, call `replit_integrations/graph_metadata_queries.get_table_columns(table_name)` and look up the specific column name in the result. Accumulate MATCH / MISSING_IN_SQLITE / TABLE_NOT_FOUND rows, print the matrix, and exit non-zero if any MISSING_IN_SQLITE row exists.

3. **Wire into CI** — Add `python scripts/verify_metadata_meaning.py` as a step in `scripts/post-merge.sh` after the existing test suite. On missing ArangoDB credentials the script prints SKIP and exits 0 (CI-safe).

## Relevant files
- `replit_integrations/metadata_query_templates.py` — `intent_concept_elevations()` and other semantic SQL templates
- `replit_integrations/graph_metadata_queries.py` — `get_table_columns()`, `get_all_table_names()`
- `hf-space-inventory-sqlgen/solder_engine.py:78-130` — `SolderEngine.load_approved_bindings()`
- `hf-space-inventory-sqlgen/graph_sync.py` — ArangoDB connection pattern and `elevates` edge structure
- `hf-space-inventory-sqlgen/arangodb_helpers/manufacturing_graph_version_0_0_1.py` — `column_key()` parsing convention
- `hf-space-inventory-sqlgen/tests/test_bridge_collection_health.py` — skip-on-no-arango pattern to replicate
- `scripts/post-merge.sh`
