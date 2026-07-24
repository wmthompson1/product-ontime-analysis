# Manufacturing SQL Semantic Layer — HF Space

## Overview
A production-ready semantic layer for manufacturing business intelligence, built around the **Solder Pattern**: all SQL comes from SME-approved ground-truth snippets, never from LLM generation. Natural-language questions are routed deterministically through a graph-theoretic semantic layer to pre-approved SQL. SQLite holds the schema metadata and bridge tables (source of truth); ArangoDB holds the graph-based semantic layer. The UI is a Gradio app hosted as a Hugging Face Space.

The repo also contains supporting Flask/Astro demos and educational Python scripts from an Advanced RAG study sequence.

## User Preferences
Preferred communication style: Simple, everyday language.
Technical preferences: LangChain for semantic layer, comprehensive safety guardrails for SQL execution, production-ready architecture with monitoring.
JavaScript framework interest: Exploring Astro as modern frontend framework to complement Flask backend.
Learning path: Advanced Python for business applications, preparing to work with APIs at aerospace manufacturing company, enrolled in AI learning for Business leaders (Berkeley Haas).
Capstone project: Semantic layer using LangChain for Berkeley Haas AI strategy class — natural language to SQL conversion for manufacturing industry.
Development approach: Learning-first methodology. Systematic `123[n..]_Entry_Point_Topic.py` naming convention for Frank Kane Advanced RAG study sequence.
API management: Cost-conscious, prefers demo modes before live API usage.
Synthetic sources: Always target SQLite (the local `manufacturing.db` dialect) for any synthetic SQL/DDL or synthetic data source. Real-source ground-truth files (e.g. SQL Server `Live.dbo.*` T-SQL) are faithful reference benchmarks only — never the synthetic target dialect.
Task management: Do NOT auto-create or propose follow-up tasks. Never use proposeFollowUpTasks or create project tasks unless explicitly asked.
Planning-doc retention: At the end of each planning session, resync the git-tracked `docs/plans/` folder from the gitignored `.local/tasks/` (copy the `*.md` files) so the planning docs are preserved in git history. The user may also ask for an on-demand resync.
Save to pods: When the user says "save to pods", save the referenced chat response (default: the most recent substantive one) as a dated markdown file in `docs/pods/` (`YYYY-MM-DD_short-topic.md`) so it is git-tracked and easy to copy.
Cascading selectors: columns may be added but max 5 per selector row, keep dropdowns narrow, and keep filter levels concrete (real categories/ontologies, nothing abstract).

## Runtime & Setup
- **Python 3.13** (pinned). Do NOT move to 3.14 — it removes `ast.Str`, which SQLGlot/SQLMesh AST handling depends on. Replit runtime module: `python-base-3.13`; virtualenv at `.pythonlibs`.
- **Python upgrade: TABLED** (per private-repo Plan-014, 2026-07-17). Upstream fix is merged — SQLMesh PR #5850 replaces astor/`ast.Str` with `ast.unparse` — but wait for a *released* SQLMesh version containing it, then validate in a disposable venv (expect one-time snapshot refingerprinting on `sqlmesh migrate`, no backfills) before touching the working environment. Never install Jupyter/pyzmq into the SQLMesh runtime env.
- Install deps with `uv pip install` from `requirements.txt` + `hf-space-inventory-sqlgen/requirements.txt`. Do NOT use `uv sync` — `uv.lock` is stale and intentionally unused.
- `pyproject.toml` sets `requires-python = ">=3.13"`.

## How to Run
- **HF Space app** (primary): workflow `HF Space Inventory SQL` → `cd hf-space-inventory-sqlgen && PORT=5000 python app.py`. FastAPI + Gradio, **webview on port 5000** (Replit preview default). Code default stays `PORT=8080` for Hugging Face deployment. Entry point `hf-space-inventory-sqlgen/app.py`.
- **Flask demo**: workflow `Flask App` → `FLASK_PORT=3000 python main.py` (port 3000, console).
- **Database**: `hf-space-inventory-sqlgen/app_schema/manufacturing.db` (SQLite, WAL mode). Gitignored — verify migrations via `sqlite3` dumps, not file copies.
- **Fresh clone / missing DB**: `cd hf-space-inventory-sqlgen && python scripts/bootstrap_db.py` — one-command idempotent rebuild (schema → seeder → full migration chain → MRP readiness check). SQLite-only, needs no Arango or API keys. Safe to re-run on an existing DB.
- **Partial bootstrap**: `python scripts/bootstrap_db.py --stop-after <migration_name>` stops right after that step (basename or full STEPS path; fails closed on unknown names; MRP check skipped). E.g. `--stop-after ship_august_first_bucket.py` yields the supported pre-collection AR state (1 engineered Disputed invoice, no receivable_payment yet).
- **Graph**: ArangoDB graph `manufacturing_graph` in database `manufacturing_graph` (name read from `ARANGO_DB`).
- **Full gate**: `scripts/post-merge.sh` runs the whole test + parity suite. It exceeds the bash-tool 120s limit — run detached or in the foreground with care.

## System Architecture

### Backend
- **Framework**: FastAPI (ASGI, uvicorn) with Gradio mounted at `/gradio`.
- **Semantic Layer — SolderEngine** (`solder_engine.py`): SQLGlot-based assembly of SME-approved SQL snippets; multi-dialect (SQLite, T-SQL, PostgreSQL, MySQL, BigQuery). Validates each snippet against a **structural fingerprint** (base tables + canonical join edges) and fails closed on drift or unrecognized joins. Also assembles **metric SQL** from a concept's `computation_template` + `resolves_to` variable bindings, failing closed on missing / extra / conflicting / static / unresolvable bindings so a define-once template yields identical SQL across perspectives.
- **Dispatcher**: closed-vocabulary router using the HuggingFace Inference API (Mistral-7B-Instruct) as a classifier only; routes to SolderEngine (never generates SQL).
- **Sync**: SQLite triggers populate a `graph_sync_queue` table; the `sync_watcher.py` daemon polls it and syncs bridge rows to ArangoDB. `graph_sync.py` performs the sync; a GitHub Actions nightly cron runs it too.
- **`GET /mcp/tools/get_resolves_to`**: read-only adapter exposing the metric/template variable bindings for cross-repo interface parity (SQLite is the source of truth; enriched with the canonical column-node key from ArangoDB, with a deterministic offline fallback).

### Frontend (Gradio tabs)
Schema Browser · Ground Truth SQL · Copilot Context Builder · Semantic Graph · Bridge Health · Graph Sync · Query Palette · Ask a Question · Masking Matrix · Metrics · MRP Schedule.
- **Metrics**: pick a metric concept → plain-language description, dialect-agnostic `computation_template`, variable→column→table lineage, table meta-context, and the assembled SQL for a chosen dialect.
- **MRP Schedule**: pick a planning part → time-phased MRP grid (open demand netted against on-hand + WO/PO scheduled receipts across Past Due + 6 monthly buckets, lot-for-lot planned receipts, lead-time-offset planned releases). Read-only, deterministic, anchored to a data-derived as-of date (`AS_OF = MAX(work_order.close_date)`).

### Key Concepts
- **Metric templates**: a metric is an existing concept node identified by duck typing (`computation_template` is non-empty; the old `concept_type` column is removed). Each `{variable}` placeholder binds to a physical column via a `resolves_to` edge. Never static SQL.
- **MRP engine** (`mrp_engine.py`): read-only, deterministic horizon + netting helpers. `validate_planning_inputs` and `compute_mrp_grid` fail closed unless every in-horizon demand part has a positive lead time and a real supply basis.
- **Define Relationship mockup** (React/Vite): `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`, served by the mockup-sandbox Vite server (port 23636), connects to the app at `/mcp/*`.

### Ledger view registration
Newly SME-approved ledger queries added to `reviewer_manifest.json` must also be added to `LEDGER_VIEW_BINDING_KEYS` in `view_ontology_extractor.py`, or they will be silently missing from the ontology mosaic (regression gate: `tests/test_ledger_view_ontology.py`).

### Approval-copy CSVs (repo root)
SME-editable CSVs at the repo root mirror into SQLite overlay tables on boot (idempotent upsert, never blocks boot):
- `masking_matrix.csv` / `masking_type.csv` — masking DAG + reference lookup (`masking_matrix.py` / `masking_type.py`); the receiving certificate imports only `status == active` rows.
- `field_descriptions.csv` — plain-language description per graph column node (`field_description_pipeline.py`; regenerate via `replit_integrations/seed_field_descriptions.py --build-graph-csv`).
- `table_descriptions.csv` — table-level meta-context (`table_description_pipeline.py`).

**Overlay-only by design**: descriptions and meta-context are NEVER written onto graph column nodes, so `graph_metadata.json` stays byte-identical.

### Graph metadata & parity gates (run by `post-merge.sh`)
- `graph_metadata.json` is serialized FROM the `sql_graph_nodes` / `sql_graph_edges` tables; bump `SCHEMA_VERSION` when re-freezing.
- **SQL↔file** (`replit_integrations/sql_graph_parity_check.py`): proves `graph_metadata.json` matches the `sql_graph_*` tables field-for-field. This is the authoritative acceptance gate.
- **SQL↔AQL** (`replit_integrations/sql_aql_parity_check.py --skip-on-missing`): compares the `sql_graph_*` tables to the live ArangoDB graph. NOTE: the live graph is on the legacy `concept_`-prefixed key model and is not synced here, so this check fails independently (pre-existing, out of scope) — it is reachable-but-stale, so `--skip-on-missing` does not skip it.
- **Field-description coverage** (`replit_integrations/field_description_coverage_check.py`): every graph column node described exactly once, no extras, none empty.
- **Grep gates**: no retired-perspective graph surfaces (`scripts/check_legacy_perspective_refs.py`); no hardcoded `"semantic_graph"` literals outside `migrations/`.

### Tests
All tests run via `scripts/post-merge.sh` (all passing except the out-of-scope live-AQL parity noted above). Test files live in `tests/` and `hf-space-inventory-sqlgen/tests/`. See `post-merge.sh` for the authoritative list.

## Key Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `ARANGO_HOST` | — | ArangoDB connection URL (with port) |
| `ARANGO_USER` | — | ArangoDB username |
| `ARANGO_ROOT_PASSWORD` | — | ArangoDB password |
| `ARANGO_DB` | `manufacturing_graph` | Database and graph name |
| `ERP_INSTANCE_NAME` | `ERP_Instance_1` | ERP source label shown in UI |
| `OPENAI_API_KEY` | — | OpenAI embeddings / AI drafting (optional) |
| `TAVILY_API_KEY` | — | Tavily search for RAG (optional) |
| `GRAPH_SYNC_ALERT_WEBHOOK` | — | Slack webhook for nightly sync-failure alerts |
| `QUERY_API_KEY` | — | API key guard for SQL generation endpoints |

## Slack Alerts for Nightly Sync Failures
`.github/workflows/graph-sync-on-change.yml` posts a Slack Block Kit alert whenever a step fails (including the 2 AM UTC scheduled run), gated on `GRAPH_SYNC_ALERT_WEBHOOK`. To enable: create a Slack Incoming Webhook, then add its URL as the GitHub Actions repository secret `GRAPH_SYNC_ALERT_WEBHOOK` (Settings → Secrets and variables → Actions). If the secret is unset, the alert step is skipped silently and a summary is still written to the Actions step-summary tab.

## External Dependencies
Flask, FastAPI, SQLAlchemy, sqlite3, LangChain, LangGraph, Gradio, SQLGlot, python-arango, FAISS, pandas, openpyxl, xlrd, requests, httpx, mcp, trafilatura, beautifulsoup4, lxml, Faker, sdv, sdmetrics
