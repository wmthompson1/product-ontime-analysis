# GL Metric Concepts & resolves_to Bindings

## What & Why
Refine the ontology with define-once GL metric concepts: add concept nodes with dialect-agnostic `computation_template`s whose `{variable}` placeholders bind to the new GL columns via `resolves_to` edges, so the Metrics tab can assemble identical SQL across perspectives — the same pattern the MRP concepts use.

## Done looks like
- 3–5 new metric concepts, e.g. **WIPBalance** (net WIP postings for a work order), **ReceivedNotInvoiced**, **AccountBalance** (net of a GL account), **CostAbsorbed** (total relieved to finished goods) — each an existing-style concept node identified by a non-empty `computation_template`, never static SQL.
- Every template variable binds to a physical column through a `resolves_to` edge; SolderEngine assembles the metric SQL and its fail-closed binding validation passes (no missing/extra/conflicting/static/unresolvable bindings).
- Concepts appear in the Metrics tab with plain-language description, lineage (variable → column → table), table meta-context, and assembled SQL per dialect.
- Concepts linked into the General_Ledger perspective vocabulary; seeded via the elevations seed path so a fresh bootstrap + graph restore reproduces them (keep seed and export in sync — re-export must not surface edges the seed doesn't define).
- Graph re-frozen (SCHEMA_VERSION bump); sql_graph parity and field-description coverage gates pass.

## Out of scope
- Ground-truth views (separate task).
- Live ArangoDB concept migration.

## Steps
1. **Define concepts & templates** — pick the metric set, write templates and plain-language descriptions consistent with existing MRP metric concepts.
2. **Bindings & seeding** — create resolves_to edges in the seed path, then export to the sql_graph tables and re-freeze.
3. **Verify assembly** — assemble each metric via SolderEngine in at least SQLite + T-SQL dialects, confirm Metrics tab display, run the gates.

## Relevant files
- `hf-space-inventory-sqlgen/solder_engine.py`
- `replit_integrations/sql_graph_parity_check.py`
- `scripts/post-merge.sh`
