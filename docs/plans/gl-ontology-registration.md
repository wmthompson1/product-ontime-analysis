# Register GL Tables in the Semantic Graph

## What & Why
Make the new `account` and `gl_transaction` tables first-class citizens of the ontology: graph nodes, structural edges, plain-language descriptions, and a re-frozen `graph_metadata.json` — so the Schema Browser, Semantic Graph tab, and all parity gates recognize them.

## Done looks like
- Both tables appear as table nodes with all their columns as column nodes in the `sql_graph_nodes`/`sql_graph_edges` tables, with `contains` and `references` structural edges derived from the declared FKs (gl_transaction → account, and linkage columns to work_order/purchase_order/part where FKs are declared).
- `graph_metadata.json` re-frozen with a `SCHEMA_VERSION` bump; `sql_graph_parity_check.py` passes (this is the authoritative gate — live-Arango parity remains out of scope per its known pre-existing drift).
- `field_descriptions.csv` gains a plain-language description for every new column node (regenerated via the seed script's `--build-graph-csv` path) and `table_descriptions.csv` gains meta-context rows for both tables; the field-description coverage check passes (every node described exactly once, no extras, none empty).
- New tables visible in the Gradio Schema Browser and Semantic Graph tabs.

## Out of scope
- Concepts, metrics, ground-truth views, and perspective wiring (separate task).
- Live ArangoDB graph migration.

## Steps
1. **Graph node/edge registration** — add the two tables and their columns/edges to the sql_graph source tables following the existing registration pattern.
2. **Descriptions** — author field and table descriptions in the approval-copy CSVs and regenerate; keep descriptions overlay-only (never written onto graph nodes).
3. **Re-freeze & gates** — export graph_metadata.json with SCHEMA_VERSION bump; run sql_graph_parity_check and field_description_coverage_check to green.

## Relevant files
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/field_description_coverage_check.py`
- `replit_integrations/seed_field_descriptions.py`
- `field_descriptions.csv`
- `table_descriptions.csv`
- `scripts/post-merge.sh`
