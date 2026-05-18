# GitHub Copilot Instructions

## The Single Most Important Rule

**All SQL in this system comes from SME-approved snippets. The LLM is a classifier only — it never generates SQL.**

Any suggestion that has an LLM writing, constructing, or interpolating SQL is architecturally wrong for this codebase.

---

## Project Overview

This is a **Manufacturing SQL Semantic Layer** for aerospace manufacturing business intelligence. It routes natural language questions through a deterministic graph to SME-approved SQL snippets, assembles them via the SolderEngine, and returns governed, auditable query results.

The project is organized as a **monorepo** running on Replit with three services and two SQLite databases as the canonical source of truth.

---

## Architecture

### Three-Service Layout

| Service | Entry Point | Port | Role |
|---|---|---|---|
| Flask API gateway | `main.py` | 5000 / ext 80 | Public REST API, proxies to HF Space |
| FastAPI + Gradio | `hf-space-inventory-sqlgen/app.py` | 8080 | Core engine, Gradio UI, MCP endpoints |
| Astro frontend | `hello-astro/` | 4321 | Frontend shell |

### Routing Chain (the Solder Pattern)

```
Natural language question
    → ProductionDispatcher
        LLM (Mistral-7B-Instruct via HuggingFace Inference API)
        classifies ONLY → Intent + Concept + Perspective
        (keyword mock fallback when no API key)
    → ArangoDB graph traversal
        Intent --operates_within--> Perspective
        Intent --elevates(weight=1)--> Concept
        Intent --bound_to--> Binding (APPROVED only)
    → Binding resolves to an APPROVED .sql snippet file
    → SolderEngine (SQLGlot)
        assembles final SQL: alias renaming, table qualification,
        CTE construction, multi-dialect transpilation
    → Result returned — zero LLM-generated SQL ever executed
```

### OUT_OF_SCOPE Detection

If the Dispatcher cannot map the question to a known Intent, it returns `OUT_OF_SCOPE` and no SQL is attempted. Do not bypass this check.

---

## Key Source Files

```
hf-space-inventory-sqlgen/
  app.py                    FastAPI + Gradio app; init_database(); all endpoints
  solder_engine.py          SQL assembly from approved snippets (SQLGlot)
  production_dispatcher.py  Semantic router — LLM classifier only, never SQL
  graph_sync.py             Syncs manufacturing.db → ArangoDB graph
  arangodb_persistence.py   ArangoDB connection, graph persistence, config
  semantic_reasoning.py     Graph traversal helpers
  app_schema/
    manufacturing.db        Authoritative SQLite — intents, concepts,
                            perspectives, bindings, concept_fields, seed data
    schema_sqlite.sql       DDL + seed (CREATE TABLE IF NOT EXISTS throughout)
    ground_truth/           Approved .sql snippet files (one per binding)

main.py                     Flask gateway; _load_anchored_env() at top
config.py                   SQLALCHEMY_DATABASE_URI

Utilities/
  ArangoFixtures/
    load_fk_edges.py        FK edge loader → ArangoDB (stable, important logic)
    load_bridge_edges.py    MAPS_TO_CONCEPT table-to-concept bridge edges
    persist_semantic_graph_to_arango.py
    verify_graph.py         100% table-to-semantic reachability assertion
  SQLMesh/analysis/impact/
    foreign_key_iterator.py Extracts FKs from ERP DDL
    foreign_key_hierarchy.py BFS hierarchy builder
    output/schema_catalog.db FK + column catalog (251 columns, 15 FKs)

docs/
  arango_graph_queries.md   AQL traversal reference — 6 core patterns + health check
```

---

## Data Layer

### Two Canonical SQLite Databases

| Database | Path | Purpose |
|---|---|---|
| `manufacturing.db` | `hf-space-inventory-sqlgen/app_schema/manufacturing.db` | Production data + semantic layer (intents, concepts, perspectives, bindings) |
| `schema_catalog.db` | `Utilities/SQLMesh/analysis/impact/output/schema_catalog.db` | ERP FK relationships + DDL column catalog |

**There is no other canonical SQLite database.** Do not create or reference a third database.

### ArangoDB Graph (`manufacturing_graph`)

- **306 nodes, 431 edges** (current state)
- **Two graph layers** — do not mix them:
  - Uppercase collections (`ELEVATES`, `OPERATES_WITHIN`, etc.) — older schema layer, vertex IDs use `manufacturing_graph_node/` prefix
  - Lowercase collections (`elevates`, `operates_within`, `intents`, `concepts`, `perspectives`, `bindings`) — **active layer**, maintained by `graph_sync.py`, use this for all new development
- **Synced from** `manufacturing.db` via `graph_sync.py` — ArangoDB is derived, SQLite is the source of truth
- Connection config lives in `arangodb_persistence.py` (reads `ARANGO_ROOT_PASSWORD`, `ARANGO_USER`, `ARANGO_DB` env vars)

### SQLMesh / DuckDB

- 41 virtual production-layer models under `Utilities/SQLMesh/`
- DuckDB is the SQLMesh execution engine
- Models are read-only views over the ERP schema; do not write to them

---

## Semantic Graph Model

```
Intent  --operates_within-->   Perspective
Intent  --elevates(w=1)-->     Concept        (1=use, 0=neutral, -1=suppress)
Intent  --bound_to-->          Binding        (→ approved .sql file)
Perspective --uses_definition--> Concept
Table   --FOREIGN_KEY-->       Table
Table   --HAS_COLUMN-->        AtomicColumn
```

**Elevation weights are binary switches** — 1 means select this concept for this intent, -1 suppresses it. SolderEngine reads SUPPRESSES edges and emits NULL for suppressed concepts. Do not treat weights as scores or rankings.

### Binding States

| Status | Behavior |
|---|---|
| `APPROVED` | SolderEngine uses this snippet |
| `PENDING` | Skipped at runtime — awaiting SME review |
| `REJECTED` | Never used |

Currently: 17 APPROVED, 2 PENDING (`quality_ncm_cost_20260209_193816`, `gt_ncm_by_employee_20260210_230752`).

---

## Environment Variables

Loaded via `_load_anchored_env()` at the top of `main.py` and `app.py`. This function walks up the directory tree (up to 3 levels) looking for a `.env` file, loads it with `override=False` so platform-injected secrets (Replit) are never overwritten.

| Variable | Used By | Notes |
|---|---|---|
| `FLASK_PORT` | `main.py` | Defaults to 5000; set to 5002 locally to avoid Kestrel collision |
| `PORT` | `app.py` (uvicorn) | Defaults to 8080 |
| `OPENAI_API_KEY` | Embeddings, RAGAS | |
| `TAVILY_API_KEY` | Advanced RAG | |
| `ARANGO_ROOT_PASSWORD` | ArangoDB | |
| `ARANGO_USER` | ArangoDB | |
| `ARANGO_DB` | ArangoDB | Fail-fast: RuntimeError if missing |
| `QUERY_API_KEY` | `/api/arango-sync` endpoint | Bearer token for sync endpoint |

**Local triple-port cleanroom** (when running alongside .NET / DAB locally):
- Kestrel: 5000 (ASP.NET default — do not touch)
- DAB / MCP server: 5001 (`DAB_PORT=5001` in parent `.env`)
- Flask: 5002 (`FLASK_PORT=5002` in parent `.env`)

---

## SQL Safety Rules

- All SQL is read-only SELECT — no INSERT, UPDATE, DELETE, DROP, or DDL
- SQL injection prevention is enforced in the semantic layer
- Use parameterized queries for any direct SQLAlchemy calls
- The SolderEngine's `execute_sql` endpoint validates operation type before execution

---

## Schema Conventions

- All 32 ERP tables use `CREATE TABLE IF NOT EXISTS` — incremental loading is safe by design
- Seed data uses `INSERT OR IGNORE` — re-running `init_database()` is idempotent
- Foreign key naming: `{table}_{column}_fk` pattern
- SQLite WAL mode is enabled on `manufacturing.db` for concurrency

---

## File Naming Conventions

- Entry point study scripts: `{number}_Entry_Point_{topic}.py` (Frank Kane Advanced RAG series)
- Ground truth SQL files: `{binding_key}.sql` in `app_schema/ground_truth/`
- ArangoDB fixture loaders: `load_{edge_type}.py` in `Utilities/ArangoFixtures/`
- Test files: `test_` prefix

---

## Code Style

- Python >= 3.11
- Type hints on all function signatures
- Google-style docstrings
- snake_case for modules, variables, functions; PascalCase for classes; UPPERCASE for constants
- Try/except with meaningful error messages — no silent fallbacks
- Never hardcode API keys, ports, or credentials — always read from environment

---

## What Not to Do

- Do not suggest LLM-generated SQL — the entire architecture exists to prevent this
- Do not write to `schema_catalog.db` — it is a derived artifact from ERP DDL analysis
- Do not add a third SQLite database without explicit instruction
- Do not bypass the `APPROVED` binding check in SolderEngine
- Do not mix the uppercase and lowercase ArangoDB graph layers
- Do not set `override=True` in `load_dotenv` — platform secrets must not be overwritten
- Do not hardcode ports — always use the env var with a safe default
