# Sectioned Join-Topology Display

## What & Why
The Join Topology tab in the view-ontology mosaic currently flattens every join in a governed view into one table, mixing the outer query's base-table joins with joins that live inside derived subqueries (e.g. the PRA view's `rcv`/`inv` aggregates). SQLGlot already walks each SELECT scope separately, so the display should render the topology in sections — outer query first, then one section per derived-subquery/CTE scope — so an SME can see at a glance which joins are structural spine and which are internal scaffolding of an aggregate.

## Done looks like
- The Join Topology tab shows the outer query's joins in a top section, followed by one clearly labeled section per derived-table or CTE scope (labeled by its alias, e.g. `rcv`, `inv`).
- Flat views (like the new Three-Way Match Coverage spine) render exactly as before — a single outer section, no empty scaffolding sections.
- The ontology data model records which scope each join belongs to; previously seeded ontology rows still load without error (missing scope defaults to the flat/legacy rendering).
- Extractor tests cover: a flat view (one scope), a view with derived subqueries (multiple scopes with correct alias labels), and a CTE-based view.

## Out of scope
- No changes to structural-fingerprint validation or the registered fingerprints (`join_edges` / `unresolved_joins` stay as they are — this is display/ontology metadata only).
- No changes to any governed SQL snippets.
- No re-registration of snippets; `graph_metadata.json` stays byte-identical.

## Steps
1. **Scope-aware extraction** — extend the join extractor so each extracted join relationship carries a scope label: outer query vs. the alias of the derived subquery or CTE whose SELECT it came from. Keep the existing dedup semantics within a scope.
2. **Ontology storage compatibility** — persist the scope label in the serialized joins metadata while keeping previously seeded rows loadable (absent scope = legacy flat).
3. **Sectioned rendering** — group the Join Topology dataframe/markdown by scope with clear section labels; outer scope first, subquery scopes after, flat views unchanged.
4. **Tests** — extend the extractor and mosaic tests for the three shapes (flat, derived-subquery, CTE); run each test file individually (gate-style), never in one big pytest batch.

## Relevant files
- `hf-space-inventory-sqlgen/view_ontology_extractor.py:123-168`
- `hf-space-inventory-sqlgen/app.py:6546-6820`
- `hf-space-inventory-sqlgen/tests/test_view_ontology_extractor.py`
- `hf-space-inventory-sqlgen/tests/test_ontology_mosaic.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/payables_partialreceiptaccrual_20260708_000004.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/payables_threewaymatchcoverage_20260708_000005.sql`
