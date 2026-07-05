# GitHub Copilot Instructions

## Build, test, and lint commands

### Main local entry points

```bash
npm run dev          # Flask + Astro
npm run dev:all      # Flask + Astro + HF Space
npm run flask        # Flask gateway (main.py)
npm run astro        # Astro frontend in astro-sample/
npm run hf-space     # Core FastAPI/Gradio semantic layer
```

### Build and static checks

```bash
npm run astro:build

cd artifacts/mockup-sandbox
npm ci
npm run typecheck
npm test

cd Utilities/SQLMesh
sqlmesh info
sqlmesh test --verbose
```

There is no single repo-wide lint command. Existing CI relies on targeted type-checks and test suites instead.

### Targeted test commands

```bash
# MCP server tests
./scripts/venv_setup.sh
.venv/bin/python -m pytest -q mcp_server/tests
.venv/bin/python -m pytest -q mcp_server/tests/test_app.py

# MCP server smoke run
./scripts/run_smoke_locally.sh 8000

# HF Space / semantic-layer tests
python -m pytest hf-space-inventory-sqlgen/tests/test_sync_triggers.py -k TestFreshDbFromRealSchema -v --tb=short
python -m pytest hf-space-inventory-sqlgen/tests/test_prune_stale_containment.py -v
python hf-space-inventory-sqlgen/tests/test_resolution_messages.py

# SQLMesh single test file or model
cd Utilities/SQLMesh
sqlmesh test tests/test_full_model.yaml
```

## High-level architecture

This repository is a monorepo with several runnable surfaces, but the governed manufacturing semantic layer lives in `hf-space-inventory-sqlgen/`.

1. `main.py` is the Flask gateway. It loads `.env` by walking upward from the file location, initializes the root SQLite-backed Flask app, and exposes lightweight health/API routes.
2. `hf-space-inventory-sqlgen/app.py` is the core service. It hosts the FastAPI API, Gradio UI, MCP endpoints, SQLite metadata bootstrap/migrations, masking metadata, and semantic-layer endpoints.
3. `hf-space-inventory-sqlgen/production_dispatcher.py` classifies a natural-language question into controlled vocabulary only. It does not generate SQL.
4. `hf-space-inventory-sqlgen/solder_engine.py` resolves APPROVED bindings from `app_schema/ground_truth/reviewer_manifest.json`, loads SME-authored SQL snippets, and assembles final SQL with SQLGlot. Missing bindings or missing snippet text are fail-closed conditions.
5. `hf-space-inventory-sqlgen/graph_sync.py` derives the active ArangoDB graph from SQLite. SQLite is the source of truth; ArangoDB is a synced projection.
6. `Utilities/SQLMesh/` is a separate DuckDB/SQLMesh analytics layer. It reuses masking helpers from `hf-space-inventory-sqlgen/` and is validated with `sqlmesh test`, not by hand-written SQL.
7. `mcp_server/` is a smaller standalone FastAPI scaffold with its own smoke tests. Do not confuse it with the main semantic-layer service in `hf-space-inventory-sqlgen/`.

## Key conventions

- **Never have the model write SQL.** In this repo, the LLM is only a classifier/router. Executable SQL must come from SME-approved snippets in `hf-space-inventory-sqlgen/app_schema/ground_truth/` and the reviewer manifest.
- **Treat SQLite as canonical.** The important production database is `hf-space-inventory-sqlgen/app_schema/manufacturing.db`. `Utilities/SQLMesh/analysis/impact/output/schema_catalog.db` is derived metadata, not a place to add new source-of-truth state.
- **Use the active graph layer, not retired perspective traversals.** New work should follow the bridge-row model (`Perspective_Intents`, `Perspective_Concepts`) and current `graph_sync.py` constants. Tests explicitly guard against reintroducing legacy `perspectives`, `operates_within`, or `uses_definition` surfaces.
- **Metadata keys are four-part identities.** In `app.py`, metadata tables such as `api_field_descriptions`, `dab_field_definitions`, and masking policy tables use `(source_database, schema_name, table_name, column_name)` keys. Do not regress them to older table/column-only keys.
- **Startup schema changes are additive and idempotent.** The repo consistently uses `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`, and self-healing startup migrations so the SQLite schema can be re-initialized safely.
- **Environment loading must preserve injected secrets.** Both `main.py` and `hf-space-inventory-sqlgen/app.py` use `_load_anchored_env()` with `load_dotenv(..., override=False)`. Do not switch that to `override=True`.
- **Keyword fallback routing is order-sensitive.** In `production_dispatcher.py`, specific phrases must appear before broader substrings (for example `lead time demand` before `lead time`, and `committed` before `inventory`). Preserve that ordering when editing mock routes.
- **SQLMesh masking logic is shared, not duplicated.** `Utilities/SQLMesh/models/raw/` imports masking helpers that ultimately reuse canonical logic from `hf-space-inventory-sqlgen/masking_matrix.py` and `masking_type.py`.
- **Port expectations are historical and inconsistent; follow the active script you are touching.** `hf-space-inventory-sqlgen/app.py` defaults to `PORT=8080`, but root helper scripts and smoke checks often expect `8000`. If you use `hf-space:test`, `test:mcp`, or `run_smoke_locally.sh`, set `PORT=8000` for the HF/MCP service.
- **When docs disagree, trust active workflows and runnable scripts first.** The root README still describes older PostgreSQL-first flows, while current CI and the main semantic layer are centered on the SQLite-backed HF Space, `mcp_server/`, and SQLMesh utilities.
