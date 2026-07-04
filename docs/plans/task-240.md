---
title: Verify & harden the 7 pure-SQL MRP snippets end-to-end
---
# Verify & Harden MRP Snippets

## What & Why
The 7 MRP inventory concepts (AvailableToPromise, AllocatedQuantity, SafetyStock, LeadTimeDemand, MinimumStockQuantity, MaximumStockQuantity, EconomicOrderQuantity) already have APPROVED pure-SQL snippets wired into `reviewer_manifest.json` and served by SolderEngine (delivered in the now-merged authoring task). With the blueprint decision locked in — pure SQL only, no SPARQL/SQLGlot/graph-edge topology on the critical path — this task does a verification and hardening pass to prove those snippets are actually correct and durable, not just present.

The gap today: existing coverage confirms each concept resolves to a snippet and returns *some* SQL, but does not prove each snippet **executes against `manufacturing.db` and returns meaningful rows**, nor that the resolution never silently falls back to auto-generated SQL. This task closes that gap and guarantees the pure-SQL verdict holds under the gate.

## Done looks like
- Each of the 7 MRP snippets is confirmed to execute successfully against `manufacturing.db` and return meaningful, non-empty result rows (not just parse or return SQL text).
- The AllocatedQuantity and AvailableToPromise snippets are confirmed to be pure SQL over the ERP tables (no SPARQL, no graph-edge topology, no runtime SQLGlot templating) — matching the approved blueprint decision.
- Resolution for all 7 concepts is confirmed to come from the approved snippet path, never the fallback/auto-generated path (the fallback warning must not be set for any of the 7).
- `test_mrp_query_palette.py` is extended so its assertions cover live execution + non-empty rows for all 7 concepts, in addition to the existing manifest/file/solder-resolution checks.
- The full `scripts/post-merge.sh` gate passes with the strengthened tests.

## Out of scope
- Redefining or changing the set semantics of any of the 7 concepts.
- Rewriting snippets unless verification finds one that fails to execute or returns empty/incorrect rows (in which case, repair the minimum needed to satisfy the approved definition — still pure SQL only).
- Introducing any graph-edge topology, SPARQL, or SQLGlot-based assembly for these concepts.
- Adding new physical columns to the synthetic schema, or touching concepts outside these 7.

## Steps
1. **Execute-and-assert each snippet** — For all 7 concepts, run the approved snippet SQL against `manufacturing.db` and confirm it executes without error and returns meaningful, non-empty rows. Record and repair any snippet that fails to execute or returns empty results, keeping the fix pure-SQL and faithful to the approved definition.
2. **Confirm no fallback resolution** — Verify SolderEngine resolves each of the 7 concepts to its approved snippet and that the fallback/auto-generated-SQL path is never taken (the fallback warning flag stays unset for all 7).
3. **Confirm pure-SQL shape for ATP & AllocatedQuantity** — Assert both snippets are plain SQL over the ERP tables with no SPARQL / graph-edge / runtime-templating dependency, per the locked blueprint decision.
4. **Strengthen the test** — Extend `test_mrp_query_palette.py` to add live-execution + non-empty-row assertions for all 7 concepts alongside the existing checks, so a regression to naive/empty/fallback SQL fails the gate.
5. **Run the gate** — Confirm the full `scripts/post-merge.sh` suite passes end to end.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_atp_20260703_000004.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_allocated_20260703_000005.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_safetystock_20260703_000006.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_leadtimedemand_20260703_000007.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_minimumstock_20260703_000008.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_maximumstock_20260703_000009.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_eoq_20260703_000010.sql`
- `hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `scripts/post-merge.sh:118-120`