# Metrics in Graph Traversal (M4)

## What & Why
Add **metrics** to the semantic-layer graph so a metric (e.g. OEE, Delivery
Performance) is connected to the physical columns and tables it is computed
from, and so every downstream tool fetches one identical, SME-approved SQL
expression for that metric. Today 17 metric concepts already exist
(`concept_type='metric'`) but they are inert: they have no column-level lineage
edges and no single canonical "define once" formula tied to the node. This
milestone (M4) closes that gap for a focused showcase set and proves the
pattern end to end, including a screen to explore it.

This builds directly on the existing architecture:
- Metrics are **concept nodes** with `concept_type='metric'` (no new 4th node
  type) — the graph already has table / column / concept nodes.
- The metric→column mapping uses the existing **`resolves_to`** semantic edge
  (column → metric concept), differentiated by edge properties — no new
  predicate.
- The plain-English business context follows the same **dual-namespace** rule
  proved out for field descriptions: it lives on semantic (concept) nodes and
  in a UI overlay, and is **never** stamped onto physical column nodes.

### Architectural guardrails (must hold)
1. **Define once / dialect-agnostic.** Each metric node stores a
   `computation_template` written with named variable placeholders (e.g.
   `(SUM({good_count}) / SUM({total_count})) * (SUM({act_run_hrs}) / SUM({run_hrs}))`).
   Nodes store the **template, never a static per-dialect SQL string**.
2. **Variables bind through the graph.** Each `{variable}` in a template maps to
   a physical column via a `resolves_to` edge (column → metric concept) that
   carries the variable name. Multi-variable metrics produce multiple edges.
3. **SME-approved, never generated.** Templates are derived from the existing
   approved SQL snippets (the SME ground truth), not invented or LLM-generated.
   The engine substitutes variables → resolved columns and transpiles; it never
   authors formulas.
4. **Meta-context stays off physical nodes.** Plain-English descriptions live on
   the metric (semantic) node and in a UI/overlay layer only — never on the
   physical column nodes (same rule as the field-description overlay).
5. **Graph stays parity-gated.** `graph_metadata.json` remains the canonical
   frozen-per-milestone snapshot; adding the template property and the new
   edges bumps the schema version and must pass the existing parity and
   coverage gates.

## Showcase scope (this milestone)
Five existing metric concepts across multiple perspectives:
- **Delivery Performance** — `DeliveryPerformanceOps` (operations),
  `DeliveryPerformanceSupplier` (quality), `DeliveryPerformanceFinance`
  (finance).
- **OEE** — `OEEOperational`, `OEEStrategic`. OEE is the multi-variable
  stress-test that proves the multi-edge `resolves_to` binding and transpilation.

## Done looks like
- For each showcase metric, the graph can answer "what is this built from?" —
  tracing metric → its variables → physical columns → owning tables.
- Each showcase metric has exactly one stored `computation_template`; asking any
  tool for that metric's SQL returns the same expression, correctly transpiled
  to the requested dialect (SQLite / T-SQL / PostgreSQL).
- A new **Metrics** screen lets a user pick a showcase metric and see its
  plain-English description (meta-context), its formula template, its lineage
  (variables → columns → tables), and the generated SQL with a dialect selector.
- The plain-English context appears in the UI and on the semantic nodes, with
  nothing written onto physical column nodes.
- All existing graph parity / coverage gates still pass, plus new tests for the
  metric layer.

## Out of scope
- The remaining 12 metric concepts (this milestone is the showcase 5; the rest
  follow the same pattern later).
- Generating the full surrounding query envelope (FROM / JOIN / WHERE / GROUP BY)
  from the graph — the milestone focuses on the metric **expression** ("define
  once"); existing snippets remain the full-query ground truth.
- Any LLM-based SQL or formula generation.
- Re-pointing or changing the existing 20 state/categorical `resolves_to` edges.
- Wiring the live legacy ArangoDB named graph to serve the new metric nodes (the
  HF app's legacy graph leaves concept/metric nodes inert; the new screen is
  powered from the SQLite source of truth + the engine).

## Steps
1. **Store the metric formula on the node.** Add a dialect-agnostic
   `computation_template` field to the metric concepts and carry it onto the
   metric concept node in the canonical graph export. Derive the showcase
   templates from the existing approved OEE / Delivery Performance snippets so
   the formulas stay SME-approved.
2. **Bind variables to columns via `resolves_to`.** Author the column → metric
   `resolves_to` edges for each template variable, with each edge carrying its
   variable name, so the graph captures full metric lineage (multi-variable for
   OEE). Reuse the existing concept-field binding mechanism rather than adding a
   new predicate.
3. **Single-source SQL assembly in the engine.** Give the Solder engine one
   method that, for a given metric, loads its template, resolves each variable
   to its bound physical column through the graph, substitutes, and transpiles
   to the requested dialect — returning the identical canonical expression every
   caller reuses. No formula generation.
4. **Meta-context layer for AI/table selection.** Provide the plain-English
   business context that helps choose the right table/metric: metric context on
   the semantic node, and a table-level context overlay mirroring the existing
   field-description overlay. Keep all of it off the physical column nodes.
5. **Metrics browse screen.** Add a Metrics tab to the app showing, per showcase
   metric: its description/meta-context, its formula template, its lineage
   (variables → columns → tables), and the generated SQL with a dialect selector
   to demonstrate transpilation. Power it from SQLite + the engine.
6. **Version, parity, and tests.** Bump the graph schema version and re-freeze
   the canonical snapshot; update the parity and coverage checks to cover the new
   node property and edges; add tests proving template storage, variable→column
   binding, identical-SQL "define once", cross-dialect transpilation, and the
   off-physical-node guardrail. Wire new checks into the post-merge gate.

## Relevant files
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/operations_oeeoperational_20260604_000007.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/operations_oeestrategic_20260604_000008.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/operations_deliveryperformanceops_20260604_000013.sql`
- `hf-space-inventory-sqlgen/field_description_pipeline.py`
- `hf-space-inventory-sqlgen/migrations/add_sql_graph_tables.py`
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/seed_elevations.py`
- `replit_integrations/seed_field_descriptions.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `replit_integrations/field_description_coverage_check.py`
- `replit_integrations/load_canonical_to_arango.py`
- `scripts/post-merge.sh`
- `docs/canonical_graph_construction_concept_as_node.md`
- `field_descriptions.csv`
