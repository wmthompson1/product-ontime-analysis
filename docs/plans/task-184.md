---
title: Define Relationship → SQLite source
---
# Define Relationship → SQLite source

## What & Why
Today the Define Relationship UI writes its **structural/semantic graph
relationships** (HAS_COLUMN, FOREIGN_KEY, ELEVATES/SUPPRESSES) straight into
ArangoDB via AQL UPSERT, bypassing the SQLite source we just proved is the
graph's source of truth. Only the two bridge predicates (OPERATES_WITHIN,
USES_DEFINITION) are SQLite-first. This task makes the canonical graph
predicates **read and write against the verified SQLite source** so an SME
defining a relationship updates the source of truth first, and the existing
sync pipeline (SQLite → graph_metadata.json → ArangoDB) carries it to the live
graph — with the SQL↔file and SQL↔AQL parity gates proving every hop stays
consistent.

## Done looks like
- In the Define Relationship UI, adding a HAS_COLUMN, FOREIGN_KEY, or
  ELEVATES/SUPPRESSES relationship writes the edge into SQLite first; the user
  sees the same "Add to Graph" confirmation and it appears in the edge list.
- The relationships an SME has authored survive a re-export (they are not wiped
  when the graph is rebuilt) and show up in graph_metadata.json and, after sync,
  in the live ArangoDB graph.
- The UI's edge list / counts for these predicates reflect the SQLite source
  (not a direct ArangoDB read).
- Undo removes the authored relationship from the SQLite source.
- Both parity checks remain green after an author → export → sync cycle.

## Out of scope
- Non-canonical predicates that have no edge type in the canonical model
  (BOUND_TO, MAPS_TO_CONCEPT/CAN_MEAN) — they keep their current ArangoDB-first
  path for now.
- The bridge predicates (OPERATES_WITHIN, USES_DEFINITION) — already SQLite-first,
  left unchanged.
- Any redesign of the canonical node/edge schema or the parity tooling.
- Auto-running export/sync on every write (kept as the existing explicit step
  unless we decide otherwise during build).

## Key architectural decision (needs the chosen approach)
The exporter MATERIALIZES `sql_graph_nodes`/`sql_graph_edges` by delete-then-
reinsert from upstream schema derivations every run, so authored edges cannot
live only in those tables — they would be erased on the next export.
**Recommended approach:** add a durable SME-authoring input table in SQLite
(e.g. `sql_graph_authored_edges`) that the UI writes to, and have the exporter
MERGE those authored edges into `sql_graph_edges` (after ensuring their endpoint
nodes exist) during materialization. This keeps SQLite the single source, lets
authored edges survive re-export, flows them downstream through the existing
pipeline, and keeps both parity gates meaningful. Alternative considered: write
to each predicate's existing upstream source instead of a unified authoring
table — rejected as inconsistent per-predicate and higher-risk.

## Steps
1. **Durable authoring table** — Add a SQLite table that records SME-authored
   canonical edges (predicate/edge_type, endpoints, perspective, weight, etc.),
   created in the seed, the app startup guards, and a migration, mirroring how
   the `sql_graph_*` tables are provisioned.
2. **Exporter merge** — Extend the exporter so materialization folds the
   authored edges into the canonical edge set (and adds any missing endpoint
   nodes), preserving deterministic ordering so parity still holds.
3. **commit_edge SQLite-first routing** — Route HAS_COLUMN, FOREIGN_KEY, and
   ELEVATES/SUPPRESSES to write the authoring table first (with duplicate
   protection), then best-effort sync to ArangoDB, matching the bridge-predicate
   pattern. Preserve the existing response shape and `edge_id` scheme.
4. **Reads from the source** — Add/adjust the endpoint(s) the UI uses so the
   edge list and counts for these predicates come from the SQLite source.
5. **Undo from the source** — Extend the DELETE path so undo removes the
   authored edge from SQLite (and best-effort from ArangoDB).
6. **Tests + parity** — Unit-test the new write/read/undo routing and the
   exporter merge; verify an author → export → sync cycle leaves both parity
   gates green. Wire any new tests into `scripts/post-merge.sh`.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:2303-2658`
- `hf-space-inventory-sqlgen/app.py:2661-2814`
- `hf-space-inventory-sqlgen/app.py:1620-1732`
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/load_canonical_to_arango.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `hf-space-inventory-sqlgen/migrations/add_sql_graph_tables.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx:213-310`
- `scripts/post-merge.sh`