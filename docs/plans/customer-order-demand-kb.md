# Customer Order Demand Doc

## What & Why
Produce a single ~15-page reference document on **manufacturing demand from the Customer Order perspective** for the aerospace MRP workflow. It mirrors the framing of the attached Manufacturing Demand Guide (ATP/allocation, customer order master logic, open quantity and running totals, demand→supply linkage, work orders as the supply response, shipping/unit-of-measure quantities, promise vs desired ship date, status/variance/risk, process map, review checklist, failure patterns, summary, key-terms appendix). It is grounded in the **real SQLite `manufacturing.db` demand tables** (`customer_order` ⋈ `customer_order_line`, plus `part` availability for an ATP-style view), with a runnable SQLite grounding query. Per project convention, the real Infor VISUAL T-SQL (`CUST_ORDER_LINE` / `DEMAND_SUPPLY_LINK` / `WORK_ORDER`) and the attached guide are **reference benchmarks only**; the synthetic target dialect is **SQLite**.

## Done looks like
- One markdown document (~15 pages) lives in `docs/my-mrp-kb` covering the Customer Order (demand) perspective for aerospace MRP, written in plain, everyday language.
- A runnable **SQLite** grounding query rooted in the Customer Order perspective (`customer_order` ⋈ `customer_order_line`, with a `part`-availability / ATP-style angle) is saved alongside it and verified to run against `manufacturing.db` and return real rows.
- The document embeds that query, explains it in plain language, and shows a small sample-output table.
- Wherever the synthetic SQLite model is thinner than the real ERP reference (e.g., no `demand_supply_link` table, no separate promised/desired ship-date columns, no per-line allocated qty), the document explicitly notes the gap and maps each concept to the closest available SQLite field.
- The work stays documentation-only: no schema, semantic-graph, or app-code changes; existing parity and coverage gates are untouched.

## Out of scope
- New tables or schema changes — use the existing `customer_order`, `customer_order_line`, and `part` tables; do **not** add `demand_supply_link`, ship-date columns, or allocated-quantity columns.
- Semantic-graph / `sql_graph_*` / `graph_metadata.json` changes (this is orthogonal documentation).
- App, UI, or workflow changes.
- Splitting into multiple pages or a folder of linked docs — keep it a single document, matching the parallel shop-floor doc.

## Steps
1. **Write the ~15-page document.** Author a single markdown file mirroring the attached Manufacturing Demand Guide's section flow, adapted to the synthetic SQLite Customer Order model: purpose and scope, what demand means here, the core demand tables, ATP and allocation, customer order master logic, open quantity and running totals, demand→supply linkage (and how it maps in the thinner synthetic model), work orders as the supply response, shipping and unit-of-measure quantities, promise vs desired ship date, status/variance/risk, process map, review checklist, failure patterns, summary, and a key-terms appendix.
2. **Author the grounding query.** Write a SQLite query rooted in the Customer Order perspective: `customer_order` joined to `customer_order_line` for demand (quantity, value, status), plus a `part`-availability / ATP-style derivation (on-hand minus open demand) where the data supports it. Target the SQLite `manufacturing.db` dialect.
3. **Verify the query.** Run it against `manufacturing.db` to confirm it returns meaningful rows; capture a small sample-output table to embed in the document.
4. **Embed and reconcile.** Place the query and its explained sample output inside the document, and add explicit notes wherever the synthetic SQLite model differs from the real ERP reference, mapping each demand concept to the closest available field.
5. **Confirm no regressions.** Verify only the two new files are added (docs + SQL); no schema, graph, or app changes; existing gates remain green.

## Relevant files
- `attached_assets/Manufacturing_Demand_Guide_1782683613585.md`
- `attached_assets/Demand_and_Supply_1_explained_1782683677014.md`
- `docs/my-mrp-kb/Knowledge Loop Framework - Aerospace MRP.md`
- `docs/my-mrp-kb/kb-inventory-transactions/Inventory_-_Transactions_AI_Review.sqlite.sql`
- `hf-space-inventory-sqlgen/migrations/add_wave4_traceability_tables.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
