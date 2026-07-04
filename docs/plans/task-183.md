---
title: SQL graph source tables
---
# SQL graph source tables

## What & Why
Today the canonical graph json (`replit_integrations/graph_metadata.json`) is *derived on the fly*: the exporter reads only the table registry from SQLite (`schema_nodes`) and rebuilds every column node and edge from raw PRAGMA each run. SQLite never actually stores the graph it emits, so there is no persisted SQLite representation to prove the graph json matches the database.

Create dedicated SQLite tables — names starting with `sql_` — that hold the full graph (every node and edge in the canonical 6-slot composite-key form). The exporter then writes the graph json *from these tables*, so SQLite is the literal, inspectable source of the graph and the two are provably in parity. This builds on the graph tables that already exist (`schema_nodes`, `schema_edges`, and the empty, column-aware `schema_topology_metadata`).

## Done looks like
- Two new persisted SQLite tables, `sql_graph_nodes` and `sql_graph_edges`, hold one row per graph node and per graph edge, with the same fields that appear in `graph_metadata.json` (keys, types, perspective, predicate, unique_id, weights, references, etc.).
- A "materialize" step fills these tables from the database (tables + columns + has_column / references / elevates edges) deterministically — re-running yields identical rows (no drift).
- The graph json is written *from* `sql_graph_nodes` / `sql_graph_edges`, so the file is a faithful dump of the SQLite tables. Node/edge counts in the json equal the row counts in the tables.
- A parity check reports SQLite ↔ graph-json agreement (row counts and keys match) and fails loudly on any mismatch — "we are sure SQLite matches graph."
- The tables survive app restart (defined in the schema seed / a migration, not created ad hoc).
- Existing exporter outputs and the ArangoDB load path keep working unchanged; existing tests still pass.

## Out of scope
- Renaming any existing files or Python modules (explicitly: create, don't rename).
- Changing the composite-key grammar, the ArangoDB live-graph key format, or the `elevates` semantic content.
- Building new UI; this is pipeline/data work only.
- Migrating the live ArangoDB graph to the canonical model.

## Steps
1. **Define the source tables** — Add `sql_graph_nodes` and `sql_graph_edges` to the SQLite schema (seed + a migration so they persist across restarts), with columns mirroring the canonical node and edge shapes used in the graph json. Reuse `schema_topology_metadata` where its column-aware shape fits, or supersede it cleanly if it cannot carry the composite-key fields.
2. **Materialize the graph into SQLite** — Add a step that runs the existing extraction (table + column nodes, has_column / references / elevates edges) and upserts the rows into `sql_graph_nodes` / `sql_graph_edges` idempotently and deterministically.
3. **Write the json from the tables** — Refactor the exporter so the graph document (nodes, edges, counts) is read from `sql_graph_nodes` / `sql_graph_edges` rather than re-derived from PRAGMA at write time, keeping the same output files and structure.
4. **Parity check** — Add a SQLite ↔ graph-json parity report (row counts and key sets must match) wired into the existing verification path so a mismatch fails the build.
5. **Tests** — Add tests covering table materialization (idempotent, correct counts), the json-from-tables writer, and the parity check; wire them into `scripts/post-merge.sh`.

## Relevant files
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/load_canonical_to_arango.py`
- `scripts/verify_metadata_meaning.py`
- `scripts/post-merge.sh`
- `replit_integrations/graph_metadata.json`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`