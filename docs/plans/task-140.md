---
title: Wire SUPPRESSES_FIELD_CONTEXT schema
---
# Wire SUPPRESSES_FIELD_CONTEXT Schema

## What & Why
Implement the new `SUPPRESSES_FIELD_CONTEXT` predicate end-to-end — from the Define Relationship form through the commit endpoint into ArangoDB — following the strict self-referencing schema blueprint: both `_from` and `_to` point to the same physical ERP table node (reflexive), and the target column lives as a `properties.target_field_scope` attribute on the edge, never as an independent node.

## Done looks like
- `SUPPRESSES_FIELD_CONTEXT` appears in the predicate dropdown in the Define Relationship form.
- When this predicate is selected, the Target entity panel locks to mirror the Source selection automatically (reflexive alignment; user cannot pick a different table).
- A column picker dropdown appears, populated with columns of the selected table (sourced from the existing schema API). Selecting a column updates the Live Identity Preview.
- Clicking "Add to Graph" commits an ArangoDB edge document with exactly this shape:
  ```json
  {
    "_key": "Int_PRO_PRO_001_Engineering",
    "_from": "ERP_Tables/PRODUCTION_ORDERS",
    "_to": "ERP_Tables/PRODUCTION_ORDERS",
    "predicate": "SUPPRESSES_FIELD_CONTEXT",
    "properties": {
      "perspective_category": "<selected_category>",
      "target_field_scope": "Graph_Component_Fields/<TABLE>.<COLUMN>"
    }
  }
  ```
- The `_key` follows the 5-segment deterministic pattern: `{PRE}_{src3}_{tgt3}_{NNN}_{perspective_slug}` where `{PRE}` = `Int` (for SUPPRESSES_FIELD_CONTEXT field-altering intent prefix).
- Duplicate upsert protection (AQL UPSERT) prevents creating the same edge twice.
- `SUPPRESSES_FIELD_CONTEXT` edges appear in the undo history and can be deleted.
- `pytest scripts/test_arango_graph_queries_unitTest.py -v` passes green (new test file).

## Out of scope
- Changing the schema of any other existing predicate types.
- Adding new ArangoDB vertex collections; use the existing ERP table vertex collection (verify name from `graph_sync.py` — currently referenced as `{graph_name}_node` or `ERP_Tables`).
- UI changes beyond the Define Relationship form.

## Steps
1. **Verify ERP table vertex collection name** — Read `graph_sync.py` and the ArangoDB named graph definition to confirm the exact collection name used for ERP table nodes (the `_from`/`_to` target). Update the blueprint's `ERP_Tables` placeholder to match. Also confirm or create the edge collection that will hold `SUPPRESSES_FIELD_CONTEXT` edges.
2. **Backend: add SUPPRESSES_FIELD_CONTEXT predicate handler** — In the `commit_edge` endpoint, add a new branch for `SUPPRESSES_FIELD_CONTEXT` that: resolves the source table to the correct `ERP_Tables/<TABLE>` handle, builds the reflexive `_to` from the same handle, assembles the 5-segment `_key` (`Int_{src3}_{src3}_{NNN}_{perspective}`), and runs an AQL UPSERT into the correct edge collection with the `properties` block. Add the predicate to the deletion allowlist.
3. **Backend: add column-list endpoint** — Expose a lightweight `GET /mcp/tools/list_table_columns?table=<name>` endpoint that returns the column names for a given ERP table (query the existing SQLite `manufacturing.db` schema tables). This feeds the UI picker.
4. **Frontend: column picker + reflexive lock** — In `DefineRelationship.tsx`: add `SUPPRESSES_FIELD_CONTEXT` to `PREDICATES`; when it is selected, lock the target search panel to mirror the source table and show a "reflexive" badge; add a column picker dropdown that fetches from the new columns endpoint; wire the selected column into `target_field_scope` in the commit payload; update `assembleEdgeId` to use the `Int_` prefix and `{src3}_{src3}` pattern for this predicate.
5. **Rebuild static bundle** — Run `vite build --config vite.define-relationship.config.ts`, update `index.html` hash reference, and remove the stale JS bundle from the Flask static directory.
6. **Write unit tests** — Create `scripts/test_arango_graph_queries_unitTest.py` covering: correct `_key` generation for the 5-segment pattern, reflexive `_from`/`_to` alignment, `properties.target_field_scope` format, AQL UPSERT idempotency for `SUPPRESSES_FIELD_CONTEXT`, and deletion via the existing delete endpoint.

## Relevant files
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/fixtures.ts`
- `hf-space-inventory-sqlgen/app.py:1800-2220`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `artifacts/mockup-sandbox/vite.define-relationship.config.ts`
- `hf-space-inventory-sqlgen/static/define-relationship/index.html`