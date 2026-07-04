---
title: Rename graph object to manufacturing_graph (remove semantic_graph)
---
# Rename graph object from semantic_graph to manufacturing_graph

## What & Why
ArangoDB currently shows two named graphs: `manufacturing_graph` and `semantic_graph`.
There should be exactly one — `manufacturing_graph` — which is also the database name.
The extra graph was created because `graph_sync.py` hardcoded `GRAPH_NAME = "semantic_graph"`
instead of reading from the `ARANGO_DB` env var. The naming guide in
`docs/arango_connection_naming_guide.md` already documents that both database and named
graph should be `manufacturing_graph`, so this is a code-catches-up-to-docs fix.

## Done looks like
- ArangoDB shows exactly one named graph: `manufacturing_graph`
- `semantic_graph` graph object no longer exists in ArangoDB
- All edge/vertex collections are unchanged (only the named graph wrapper is renamed)
- A live re-sync run writes the graph under the correct name
- `graph_sync.py` derives `GRAPH_NAME` from the `ARANGO_DB` env var
  (so it can never drift from the database name again)
- All AQL templates, docstrings, and migration scripts reference `manufacturing_graph`

## Out of scope
- Changing any collection names (intents, concepts, bindings, elevates, etc.)
- Changing the database name (already correct: `manufacturing_graph`)

## Steps
1. **Fix the constant in graph_sync.py** — Replace the hardcoded `GRAPH_NAME = "semantic_graph"`
   with `GRAPH_NAME = os.environ.get("ARANGO_DB", "manufacturing_graph")` and update the
   module-level docstring comment that still says "Graph name: semantic_graph".
2. **Fix the constant in drop_legacy_perspective_graph.py** — Same one-line fix:
   replace `GRAPH_NAME = "semantic_graph"` with the env-var pattern.
3. **Fix AQL template strings in semantic_reasoning.py** — Two AQL template strings
   contain the literal `GRAPH 'semantic_graph'`; replace both with `GRAPH 'manufacturing_graph'`
   (these are illustrative/legacy Cypher/AQL templates, not executable against the live DB,
   but they should be consistent).
4. **Fix the docstring in app.py** — One docstring on the Graph Sync tab references
   `` `semantic_graph` `` as the graph name; update it to `` `manufacturing_graph` ``.
5. **Drop semantic_graph and re-sync live** — Write a one-shot migration script
   (`migrations/rename_graph_to_manufacturing.py`) that: (a) connects to ArangoDB using
   `get_arango_client` / `get_arango_db` from graph_sync, (b) calls
   `db.delete_graph("semantic_graph", drop_collections=False)` if it exists,
   (c) then calls `sync_graph(dry_run=False)` to recreate the graph wrapper under the new
   name with all existing collections intact. Run it as part of this task.
6. **Verify** — After the migration, confirm ArangoDB shows only `manufacturing_graph`
   and that all 80 vertices / 41 edges are still reachable.

## Relevant files
- `hf-space-inventory-sqlgen/graph_sync.py:15,40`
- `hf-space-inventory-sqlgen/migrations/drop_legacy_perspective_graph.py:40`
- `hf-space-inventory-sqlgen/semantic_reasoning.py:615,654`
- `hf-space-inventory-sqlgen/app.py:3465`
- `docs/arango_connection_naming_guide.md`