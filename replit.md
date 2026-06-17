# Manufacturing SQL Semantic Layer — HF Space

## Overview
A production-ready semantic layer for manufacturing business intelligence, built around the "Solder Pattern": all SQL comes from SME-approved ground-truth snippets, never from LLM generation. Natural language questions are routed deterministically through a graph-theoretic semantic layer to pre-approved SQL. The system uses SQLite for schema metadata and ArangoDB for the graph-based semantic layer, with a Gradio interface hosted as a Hugging Face Space.

The project also contains supporting Flask/Astro demos and educational Python scripts from an Advanced RAG study sequence.

## User Preferences
Preferred communication style: Simple, everyday language.
Technical preferences: LangChain for semantic layer, comprehensive safety guardrails for SQL execution, production-ready architecture with monitoring.
JavaScript framework interest: Exploring Astro as modern frontend framework to complement Flask backend.
Learning path: Advanced Python for business applications, preparing to work with APIs at aerospace manufacturing company, enrolled in AI learning for Business leaders (Berkeley Haas).
Capstone project: Semantic layer using LangChain for Berkeley Haas AI strategy class — natural language to SQL conversion for manufacturing industry.
Development approach: Learning-first methodology. Systematic `123[n..]_Entry_Point_Topic.py` naming convention for Frank Kane Advanced RAG study sequence.
API management: Cost-conscious, prefers demo modes before live API usage.
Task management: Do NOT auto-create or propose follow-up tasks. Never use proposeFollowUpTasks or create project tasks unless explicitly asked.

## Current System State (May 2026)

### Python runtime baseline (June 2026)
- **Runtime: Python 3.13.11** — upgraded from 3.11. Pinned to **3.13 specifically**; do NOT move to 3.14 (3.14 removes `ast.Str`, which SQLGlot/SQLMesh AST handling depends on).
- Replit runtime module: `python-base-3.13` (the old `python-3.11` module was removed). The virtualenv lives at `.pythonlibs`, rebuilt on 3.13.
- Dependencies are installed with `uv pip install` from `requirements.txt` + `hf-space-inventory-sqlgen/requirements.txt` (not `uv sync` — `uv.lock` is stale and intentionally not used).
- `pyproject.toml` `requires-python = ">=3.13"`.
- Verified on 3.13: both apps boot (HF Space on :8080 with the Gradio UI serving, Flask on :5000), every dependency imports, and the full `scripts/post-merge.sh` gate passes.

### HF Space app — fully operational
- Entry point: `hf-space-inventory-sqlgen/app.py` (FastAPI + Gradio, port 8080)
- Database: `hf-space-inventory-sqlgen/app_schema/manufacturing.db` (SQLite, 33 tables, WAL mode)
- ArangoDB: graph `manufacturing_graph` in database `manufacturing_graph` (read from `ARANGO_DB` env var)
- Workflow: "HF Space Inventory SQL" → `cd hf-space-inventory-sqlgen && python app.py`

### What's been built and is working
- **Solder Pattern end-to-end**: NL → dispatcher → SolderEngine → SME-approved SQL (never LLM-generated)
- **ArangoDB graph**: single named graph `manufacturing_graph`, 80 vertices, 41 edges; legacy `semantic_graph` retired
- **Perspective Bridge Model**: Perspective lives as a property on bridge rows (`Perspective_Intents`, `Perspective_Concepts`) — not as a vertex collection
- **Define Relationship UI** (mockup panel): live entity search, Add to Graph wired to real endpoints, duplicate-edge protection (AQL UPSERT), undo history (last 5), edge-count badge with per-collection tooltip
- **Gradio tabs**: Schema browser, Ground Truth SQL browser, Semantic Graph + disambiguation, Bridge Health, Graph Sync, Query Palette, Ask a Question, Masking Matrix, Metrics — all showing live ERP source label
- **Metric computation templates (M4)**: a metric is an existing concept node (`concept_type='metric'`) that stores a dialect-agnostic `computation_template` with named `{variable}` placeholders — **never static SQL**. Each placeholder binds to a physical column via a `resolves_to` edge carrying `variable_name` (SQLite source: `schema_concept_fields.variable_name`). SolderEngine substitutes variables → table-qualified columns and transpiles, so a define-once template yields identical SQL across the perspectives that share it. Showcase 5: `DeliveryPerformanceOps`/`Supplier`/`Finance` (one shared on-time definition, differing only by perspective + meta-context), `OEEOperational`, `OEEStrategic`. **No new perspectives and no new nodes** were created; the 5 templates added 17 `resolves_to` binding edges (canonical: 289 nodes, 299 edges — 223 has_column, 39 references, 37 resolves_to; SCHEMA_VERSION 17).
- **Masking Matrix tab**: editable grids for the `masking_matrix` DAG and the `masking_type` reference lookup; Save full-replaces SQLite **and** mirrors the SME-facing root CSVs (`masking_matrix.csv`, `masking_type.csv`). Shows salt status (never the value) and a mask preview. The receiving certificate imports only matrix rows whose `status` is `active`.
- **Sync automation**: SQLite triggers → queue table → polling watcher (`sync_watcher.py`) → ArangoDB sync; GitHub Actions nightly cron
- **Drift alerts**: 6-hour GitHub Actions drift check with Slack Block Kit alerts (gated on `GRAPH_SYNC_ALERT_WEBHOOK` secret)
- **CI**: Consolidated `hf-space-ci.yml` runs all 7 test files; ArangoDB smoke test in `arango-legacy-smoke.yml` (nightly + on push)

### Test suite
All tests run via `scripts/post-merge.sh` (all passing):
| File | What it covers |
|---|---|
| `tests/test_field_description_pipeline.py` | Drafts (plain-language, no SQL jargon), KB-context selection, CSV round-trip, graph coverage (223/223), overlay-only guardrail (14 tests) |
| `tests/test_perspective_deprecation.py` | Graph constants, bridge lookups, legacy collection absence (8 tests) |
| `tests/test_resolution_messages.py` | Bridge-row resolution explanation strings (5 tests) |
| `tests/test_db_init_self_heal.py` | Older-schema DB self-heal: `init_sqlite_db` widens `schema_concepts` (`concept_type`/`domain`) before seeding so the seed runs to completion; resolve endpoint returns 200 (not 500) on a stale DB (2 tests) |
| `tests/test_sync_triggers.py` | SQLite trigger install/verify/remove, queue firing (21 tests) |
| `tests/test_mcp_config.py` | /mcp/config ERP name + API key reflection (5 tests) |
| `tests/test_delete_commit_edge_404.py` | Double-undo, missing edge 404 paths (5 tests) |
| `tests/test_commit_edge_duplicate.py` | AQL UPSERT idempotency for all 5 predicates (11 tests) |
| `tests/test_bridge_collection_health.py` | ArangoDB ↔ SQLite count parity (skips if offline) |
| `tests/test_sql_graph_tables.py` | `sql_graph_nodes`/`sql_graph_edges` round-trip (incl. M4 `computation_template` node + `variable_name` edge columns), ordering, doc-from-tables parity, legacy-DB rebuild (23 tests) |
| `tests/test_sql_aql_parity.py` | SQL (SQLite tables) vs AQL (live graph) parity via injected fake Arango (8 tests) |
| `hf-space-inventory-sqlgen/tests/test_metric_assembly.py` | Metric template storage, variable→column binding/lineage, define-once identical SQL, perspective fan-out yields identical SQL, conflicting/missing/static templates fail closed, cross-dialect transpile, table-description overlay round-trip, overlay-never-on-graph-nodes (12 tests) |
| `hf-space-inventory-sqlgen/tests/test_get_resolves_to.py` | `GET /mcp/tools/get_resolves_to` payload shape (6 cross-repo keys), all 11 M4 bindings present, OEEOperational + DeliveryPerformanceOps bindings + canonical `field_key`, unknown concept → empty (5 tests) |

### Graph parity gates (run by post-merge.sh)
- **SQL vs file**: `replit_integrations/sql_graph_parity_check.py` — proves `graph_metadata.json` is field-for-field identical to the `sql_graph_*` tables (emission order asserted).
- **SQL vs AQL**: `replit_integrations/sql_aql_parity_check.py --skip-on-missing` — flattens the live ArangoDB graph (drops server `_rev`) and proves it matches the `sql_graph_*` tables field-for-field (order not asserted; unreachable graph = skip, real drift = fail).

### Field-description coverage gate (run by post-merge.sh)
- `replit_integrations/field_description_coverage_check.py` — proves `field_descriptions.csv` covers every graph column node in `graph_metadata.json` exactly (223/223), every description non-empty, and no extra rows. File-vs-file (no DB/network needed).

### Grep gates (run by post-merge.sh)
- No retired perspective graph surfaces (`scripts/check_legacy_perspective_refs.py`)
- No hardcoded `"semantic_graph"` literals outside `migrations/`

## System Architecture

### Backend
- **Framework**: FastAPI (ASGI, uvicorn) + Gradio mounted at `/gradio`
- **Database**: SQLite (`manufacturing.db`, WAL mode) — source of truth for schema metadata and bridge tables
- **Graph**: ArangoDB — `manufacturing_graph` database, `manufacturing_graph` named graph; populated by `graph_sync.py`
- **Semantic Layer**: SolderEngine (`solder_engine.py`) — SQLGlot-based assembly of approved SQL snippets; multi-dialect (SQLite, T-SQL, PostgreSQL, MySQL, BigQuery). Also assembles **metric SQL** from a concept's `computation_template` + its `resolves_to` variable bindings: resolves at concept scope, dedups `variable_name`→`table.column`, and fails closed on missing / extra / conflicting / static / unresolvable-join bindings (one distinct binding per placeholder) — guaranteeing define-once → identical SQL.
- **`GET /mcp/tools/get_resolves_to`**: read-only adapter exposing the M4 metric/template variable bindings for cross-repo (public-fleet) interface parity. Reads binding rows from the SQLite source of truth (`schema_concept_fields` where `variable_name IS NOT NULL`, joined to `schema_concepts`) and enriches each with `field_key` from the live ArangoDB `resolves_to` edges (canonical column-node key, with a deterministic fallback when ArangoDB is offline). Optional `concept_name` filter; each item carries `concept, variable_name, table_name, field_name, field_key, context_hint`. **No `schema_resolves_to` table is introduced** — the existing M4 model is the single source of truth.
- **Dispatcher**: Production Dispatcher — closed-vocabulary router using HuggingFace Inference API (Mistral-7B-Instruct) as classifier only, routes to SolderEngine
- **Sync**: `sync_watcher.py` daemon polls `graph_sync_queue` SQLite table (populated by triggers); `scripts/install_sync_triggers.py` installs 9 triggers on 3 bridge tables

### Frontend (Gradio)
Tabs: Schema Browser · Ground Truth SQL · Copilot Context Builder · Semantic Graph · Bridge Health · Graph Sync · Query Palette · Ask a Question · Masking Matrix · Metrics

The **Metrics** tab lets you pick a metric concept and shows its plain-language description, the dialect-agnostic `computation_template`, the variable→column→table lineage, the table-level meta-context, and the SolderEngine-assembled SQL for a chosen dialect.

### Masking approval copies (repo root)
`masking_matrix.csv` and `masking_type.csv` live at the repo root as the SME-facing approval copies (CSV ↔ SQLite, upsert on boot). `masking_matrix.py` / `masking_type.py` manage them; `certificate_for_receiving/generate_certificate.py` reads the root `masking_matrix.csv` and imports only `status == active` rows.

### Field-description approval copy (repo root)
`field_descriptions.csv` lives at the repo root as the SME-editable approval copy of plain-language descriptions for every graph column node (223 rows, one per canonical-graph `table,column`). On boot, `app.py` upserts it into the `api_field_descriptions` overlay table (idempotent, never blocks boot) so descriptions survive a DB rebuild — mirroring the masking pattern. **Overlay-only by design: descriptions are NEVER written onto graph column nodes**, so `graph_metadata.json` stays byte-identical. `field_description_pipeline.py` manages the CSV (read/write/load + coverage helpers); `replit_integrations/seed_field_descriptions.py --build-graph-csv` regenerates it (priority: existing CSV row > curated `FIELD_DESCRIPTIONS` > fresh draft). Drafts are plain-language with no SQL jargon; AI drafting (gpt-4o-mini + KB context) is available via `--ai`, with a deterministic pattern-based fallback used when no working OpenAI key is present.

### Table-description / meta-context approval copy (repo root)
`table_descriptions.csv` lives at the repo root as the SME-editable approval copy of table-level meta-context (showcase tables: `operation`, `purchase_order`, `receiving`). On boot, `app.py` upserts it into the `api_table_descriptions` overlay table (PK `source_database` + `schema_name` + `table_name`; columns `display_name`, `description`, `ai_context`) — idempotent, never blocks boot — mirroring the field-description and masking patterns. **Overlay-only by design: this AI meta-context is NEVER written onto physical graph column nodes**, so `graph_metadata.json` stays byte-identical. `table_description_pipeline.py` manages the CSV (read/write/load helpers).

### Define Relationship mockup (React/Vite)
Location: `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`
Served by mockup sandbox Vite server (port 23636). Connects to Flask app at `/mcp/*`.

## Key Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `ARANGO_HOST` | — | ArangoDB connection URL (with port) |
| `ARANGO_USER` | — | ArangoDB username |
| `ARANGO_ROOT_PASSWORD` | — | ArangoDB password |
| `ARANGO_DB` | `manufacturing_graph` | Database and graph name |
| `ERP_INSTANCE_NAME` | `ERP_Instance_1` | ERP source label shown in UI |
| `OPENAI_API_KEY` | — | OpenAI embeddings (optional) |
| `TAVILY_API_KEY` | — | Tavily search for RAG (optional) |
| `GRAPH_SYNC_ALERT_WEBHOOK` | — | Slack incoming webhook for sync failure alerts (see below) |
| `QUERY_API_KEY` | — | API key guard for SQL generation endpoints |

## Enabling Slack Alerts for Nightly Sync Failures

The nightly graph sync workflow (`.github/workflows/graph-sync-on-change.yml`) posts a Slack Block Kit alert whenever any step fails — including the 2 AM UTC scheduled run. The alert includes the failure timestamp, branch, who triggered the run, and a direct link to the GitHub Actions log. If a bridge health drift report was written, it is included in the alert body.

**To enable alerts:**

1. Create a Slack Incoming Webhook for your workspace:
   - Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch
   - Under "Add features", choose **Incoming Webhooks** and activate them
   - Click **Add New Webhook to Workspace**, pick the channel where alerts should appear, and copy the webhook URL (format: `https://hooks.slack.com/services/…`)

2. Add the URL as a GitHub Actions repository secret:
   - In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GRAPH_SYNC_ALERT_WEBHOOK`
   - Value: the webhook URL copied above

3. That's it. The next time the nightly sync fails (or any push-triggered run fails), a Slack message is posted automatically. If `GRAPH_SYNC_ALERT_WEBHOOK` is not set, the step is skipped silently and a summary is still written to the GitHub Actions step summary tab.

## External Dependencies
Flask, FastAPI, SQLAlchemy, sqlite3, LangChain, LangGraph, Gradio, SQLGlot, python-arango, FAISS, pandas, openpyxl, xlrd, requests, httpx, mcp, trafilatura, beautifulsoup4, lxml, Faker, sdv, sdmetrics
