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

## SME-authored canonical edges are SQLite-first
The Define Relationship UI's canonical predicates (HAS_COLUMN→has_column,
FOREIGN_KEY→references, ELEVATES/SUPPRESSES→elevates) write to a separate SQLite
table `sql_graph_authored_edges` FIRST; ArangoDB is updated best-effort only and
its failure never blocks the write. The exporter MERGES those authored rows into
its derived FK/elevation feeds on every run (`_fetch_authored_edges` +
`_merge_authored_into_sources`), so authored edges survive the delete+reinsert of
`sql_graph_*` and flow through export→sync into the live graph.

**Why:** the prior code wrote canonical edges Arango-first, so they vanished on
the next exporter run (which rebuilds the graph from SQLite). SQLite is the
source of truth; anything that must persist has to live in SQLite.

**How to apply:**
- Authored rows are column→column to fold in. The UI sends *table-level* FK
  (no columns), so column-less `references`/`elevates` authored rows are honestly
  *skipped* by the merge (no fake column invented); `has_column` is always a
  no-op (the derived backbone already emits every has_column). Merge de-dupes
  against rows the derived feeds already contain.
- Weight is a binary gate: ELEVATES→1, SUPPRESSES→0 (NOT the old +1/−1).
- ELEVATES requires a non-`system` perspective (commit_edge returns 422 without).
- Endpoints resolve against `sql_graph_nodes` (the verified source), not the live
  graph — case-insensitive, stripping ` (suffix)` and any `schema.` prefix.
- edge_id for undo is `sqlite:sql_graph_authored_edges/<authored_id>`; DELETE on a
  missing id is 404. graph_stats exposes `sql_graph_authored_rows` but it is NOT
  added into `total_edges` (avoids double-counting; merged rows show up in the
  next export's edge total instead).

## SQLite gotcha: `notnull` is reserved
`notnull` is the SQLite `x NOTNULL` operator token, so a bare column named
`notnull` is a syntax error ("near \"notnull\""). It must be double-quoted
(`"notnull"`) in CREATE TABLE and INSERT column lists. Row access by name
(`row["notnull"]`) is unaffected.
