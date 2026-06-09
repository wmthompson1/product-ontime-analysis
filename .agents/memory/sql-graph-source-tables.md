---
name: SQL graph source tables
description: graph_metadata.json is serialized FROM SQLite tables; parity is enforced; SQLite quirks that bit us.
---

# SQL graph source tables (sql_graph_nodes / sql_graph_edges)

The canonical graph JSON (`replit_integrations/graph_metadata.json`) is NOT built
straight from PRAGMA anymore. The exporter (`export_graph_metadata.py`) extracts
nodes/edges, **materializes** them into the SQLite tables `sql_graph_nodes` /
`sql_graph_edges`, then **reads them back** and serializes the JSON from those
rows. So SQLite is the inspectable source of truth and the JSON is provably a dump
of the tables.

**Why:** the user wanted "SQLite will match the graph" to be provable, not
asserted — a real SQLite↔graph parity, with files/tables named `sql_*`.

**Design-priority note (from the user):** graph development is on the *critical
path* because resolving triples depends on structural containment living in the
graph. So graph design takes precedence over the SQLite relational design — the
relational schema follows the graph, not vice versa. These `sql_*` tables exist
to *mirror and prove* the graph, not to independently define the model.

**How to apply:**
- One column per JSON field; columns that apply to only one node/edge kind are
  NULL for the others. An `ordinal` column records emission order (table nodes
  before column nodes; has_column → references → elevates) so read-back is
  byte-order-identical to the old direct build.
- Booleans (`notnull`, `primary_key`, `foreign_key`) store as INTEGER 0/1 and are
  restored with `bool()`. `default_value` is the PRAGMA SQL text (always str|None).
- Any change to the node/edge JSON shape must be mirrored in: the table DDL (3
  places — `schema_sqlite.sql` seed, `app.py` startup additive guards, and
  `migrations/add_sql_graph_tables.py`), the materialize INSERT, and the
  `_node_dict_from_row` / `_edge_dict_from_row` reconstructors — or parity breaks.
- Parity is gated in `scripts/post-merge.sh` via
  `replit_integrations/sql_graph_parity_check.py` (compares counts, _key sets,
  every field, and order; ignores the doc-level `synced_at` timestamp, which is
  fresh per run and not stored).

## Two parity gates: SQL-vs-file and SQL-vs-AQL
Parity is proven on both downstream hops, reusing one comparator
(`sql_graph_parity_check._compare`, which takes `check_order` + `left`/`right`
labels):
- **SQL vs file** (`sql_graph_parity_check.py`): SQLite tables ↔
  `graph_metadata.json`. Both are deterministically ordered by `ordinal`, so
  emission order IS asserted.
- **SQL vs AQL** (`sql_aql_parity_check.py`): SQLite tables ↔ the *live*
  ArangoDB graph queried with `FOR d IN <col> RETURN d`. ArangoDB returns
  documents unordered, so order is NOT asserted. The server adds a volatile
  `_rev` (drop it) and an `_id` equal to `{collection}/{_key}` (matches our
  constructed `_id`, so keep it). Offline-tolerant: unreachable/unconfigured
  Arango is a SKIP (exit 0) unless `--require-arango`; a real field drift fails.
  Tests inject a fake `db` whose `aql.execute` replays shuffled docs — no live
  graph needed in CI.

**Why:** "the SQL matches the graph" must hold against the *live* graph, not
just the static JSON file — triple resolution runs on the live Arango graph.

## SQLite gotcha: `notnull` is reserved
`notnull` is the SQLite `x NOTNULL` operator token, so a bare column named
`notnull` is a syntax error ("near \"notnull\""). It must be double-quoted
(`"notnull"`) in CREATE TABLE and INSERT column lists. Row access by name
(`row["notnull"]`) is unaffected.
