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

## Current System State (May 2026)

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
- **Gradio tabs**: Schema browser, Ground Truth SQL browser, Semantic Graph + disambiguation, Bridge Health, Graph Sync, Query Palette, Ask a Question — all showing live ERP source label
- **Sync automation**: SQLite triggers → queue table → polling watcher (`sync_watcher.py`) → ArangoDB sync; GitHub Actions nightly cron
- **Drift alerts**: 6-hour GitHub Actions drift check with Slack Block Kit alerts (gated on `GRAPH_SYNC_ALERT_WEBHOOK` secret)
- **CI**: Consolidated `hf-space-ci.yml` runs all 7 test files; ArangoDB smoke test in `arango-legacy-smoke.yml` (nightly + on push)

### Test suite
All tests run via `scripts/post-merge.sh` (8/8 passing):
| File | What it covers |
|---|---|
| `tests/test_perspective_deprecation.py` | Graph constants, bridge lookups, legacy collection absence (8 tests) |
| `tests/test_resolution_messages.py` | Bridge-row resolution explanation strings (5 tests) |
| `tests/test_sync_triggers.py` | SQLite trigger install/verify/remove, queue firing (21 tests) |
| `tests/test_mcp_config.py` | /mcp/config ERP name + API key reflection (5 tests) |
| `tests/test_delete_commit_edge_404.py` | Double-undo, missing edge 404 paths (5 tests) |
| `tests/test_commit_edge_duplicate.py` | AQL UPSERT idempotency for all 5 predicates (11 tests) |
| `tests/test_bridge_collection_health.py` | ArangoDB ↔ SQLite count parity (skips if offline) |

### Grep gates (run by post-merge.sh)
- No retired perspective graph surfaces (`scripts/check_legacy_perspective_refs.py`)
- No hardcoded `"semantic_graph"` literals outside `migrations/`

## System Architecture

### Backend
- **Framework**: FastAPI (ASGI, uvicorn) + Gradio mounted at `/gradio`
- **Database**: SQLite (`manufacturing.db`, WAL mode) — source of truth for schema metadata and bridge tables
- **Graph**: ArangoDB — `manufacturing_graph` database, `manufacturing_graph` named graph; populated by `graph_sync.py`
- **Semantic Layer**: SolderEngine (`solder_engine.py`) — SQLGlot-based assembly of approved SQL snippets; multi-dialect (SQLite, T-SQL, PostgreSQL, MySQL, BigQuery)
- **Dispatcher**: Production Dispatcher — closed-vocabulary router using HuggingFace Inference API (Mistral-7B-Instruct) as classifier only, routes to SolderEngine
- **Sync**: `sync_watcher.py` daemon polls `graph_sync_queue` SQLite table (populated by triggers); `scripts/install_sync_triggers.py` installs 9 triggers on 3 bridge tables

### Frontend (Gradio)
Tabs: Schema Browser · Ground Truth SQL · Copilot Context Builder · Semantic Graph · Bridge Health · Graph Sync · Query Palette · Ask a Question

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
