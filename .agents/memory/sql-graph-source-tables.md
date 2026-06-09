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

## SQLite gotcha: `notnull` is reserved
`notnull` is the SQLite `x NOTNULL` operator token, so a bare column named
`notnull` is a syntax error ("near \"notnull\""). It must be double-quoted
(`"notnull"`) in CREATE TABLE and INSERT column lists. Row access by name
(`row["notnull"]`) is unaffected.
