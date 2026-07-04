---
title: Define MRP set-semantics criteria (7 concepts)
---
# Define MRP Set-Semantics Criteria

## What & Why
Seven MRP/inventory concepts were promoted into the certified semantic layer, but their SQL does not express correct **set semantics**. The architect flagged that these are *derived, state-driven conditional sets* — not simple single-column lookups — so their relational logic must be defined and SME-reviewed **before** any snippet is approved.

Current honest state:
- **ATP (AvailableToPromise)** and **AllocatedQuantity** are approved in the manifest but use **naive** logic: ATP is `on_hand − SUM(order_qty)` with no scheduled receipts, no time-phasing, and no order-status filter; AllocatedQuantity is a flat `SUM(order_qty)` by part with no WO/order-state conditioning.
- **SafetyStock, LeadTimeDemand, MinimumStockQuantity, MaximumStockQuantity, EconomicOrderQuantity** have draft snippet **files** containing proxy SQL, but they are **not in `reviewer_manifest.json`**, so SolderEngine never serves them — they still fail closed as glossary placeholders.

This task produces the ground-truth definition (the "set criteria") for all 7 concepts. It supersedes the cancelled task whose framing ("wait for ERP columns to be added") was wrong — these are derivations over existing tables, not missing columns.

This is a **definition/design deliverable only**. No snippet is approved and no manifest change is made here — that is the dependent authoring task.

## Done looks like
- A single SME-reviewable set-criteria document exists covering all 7 concepts.
- For each concept the document states, in plain language plus a precise relational specification:
  - The **set definition**: which base tables, which joins, which aggregation/window functions, and which **state conditions** (e.g. only firm/released work-order supply counts; only open/allocated customer-order demand counts) define the set.
  - Any **time-phasing / horizon** rule (e.g. ATP nets scheduled receipts against demand across the planning horizon, anchored to the data-derived AS_OF, never wall-clock).
  - Whether the set is best expressed as **pure SQL window-aggregation** or requires **Arango set-topology edges** (e.g. a consumes-allocation / reserves-capacity relationship), with a recommendation and rationale.
  - The exact SQLite tables/columns each definition depends on, confirmed to exist in `manufacturing.db`.
- The document explicitly critiques the current naive ATP and AllocatedQuantity logic and specifies the corrected set definition for each.
- No naive single-column stubs are proposed for any concept that needs relational logic.

## Out of scope
- Writing or approving any SQL snippet, editing `reviewer_manifest.json`, or adding `seed_elevations.py` bindings (that is the dependent authoring task).
- Any change to the graph metadata / `graph_metadata.json`.
- Adding new physical columns to the synthetic schema.

## Steps
1. **Inventory current logic** — Read the existing snippet files and the two approved bindings, and record exactly what set each currently computes and where it is wrong or incomplete.
2. **Define each set** — For all 7 concepts, specify the base tables, joins, aggregations/window functions, state conditions, and time-phasing rule that correctly define the set over the synthetic SQLite schema. Anchor any horizon to the data-derived AS_OF, never wall-clock.
3. **Decide the modeling surface** — For each concept, recommend pure SQL window-aggregation vs Arango set-topology edges, with rationale, so the authoring task knows whether graph edges must be added.
4. **Verify data availability** — Confirm every referenced table/column exists in `manufacturing.db` and note any gap that blocks a faithful definition.
5. **Write the SME-reviewable document** — Capture all of the above as one plain-language + precise-spec ground-truth definition document for SME sign-off.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_atp_20260703_000004.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_allocated_20260703_000005.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_safetystock_20260703_000006.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_leadtimedemand_20260703_000007.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_minimumstock_20260703_000008.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_maximumstock_20260703_000009.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_eoq_20260703_000010.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `replit_integrations/seed_elevations.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`