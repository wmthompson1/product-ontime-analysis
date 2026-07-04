# Shop Floor Work & Routing Doc

## What & Why
Produce a single ~15-page reference document on **shop floor work and routing** for the aerospace Manufacturing Resource Planning (MRP) workflow. The document is grounded in a **two-table join of `work_order` and `operation`**, treating `operation.resource_id` as the work station (per the request — no third table required). It explains how routed work flows step-by-step across work stations and how shop-floor execution data feeds the **Knowledge Loop** (Plan → Execute → Capture → Analyze → Learn → Refine), enabling iteration on routing standards. This extends the existing `docs/my-mrp-kb` knowledge base, matching the framing of the existing Knowledge Loop Framework document.

## Done looks like
- One markdown document (~15 pages) lives in `docs/my-mrp-kb` covering shop-floor execution and routing for aerospace MRP, written in plain, everyday language.
- A runnable **SQLite** query file (the two-table `work_order ⋈ operation` join, `resource_id` = work station) is saved alongside it and verified to run against `manufacturing.db` and return real rows.
- The document embeds that query, explains it in plain language, shows a small sample-output table, and includes a dedicated section on how the execution data closes / iterates the Knowledge Loop.
- The work stays documentation-only: no schema, semantic-graph, or app-code changes; existing parity and coverage gates are untouched.

## Out of scope
- New tables or schema changes — `work_order`, `operation`, and `shop_resource` already exist; nothing is altered.
- Semantic-graph / `sql_graph_*` / `graph_metadata.json` changes (this is orthogonal documentation).
- Splitting into multiple pages or a folder of linked docs — the user chose a single document.
- Any third table in the grounding query — keep it strictly `work_order ⋈ operation` with `resource_id` as the work station (a human-readable work-station name from `shop_resource` may be mentioned in prose only, not added as a join).
- App, UI, or workflow changes.

## Steps
1. **Write the ~15-page document.** Author a single markdown file on shop floor work and routing for aerospace MRP, structured like the existing Knowledge Loop Framework doc: executive overview, the work_order→operation routing data model, routing fundamentals (sequence_no, routing_template, operation type), shop-floor execution / Production Activity Control (op status Q/S/C, dispatch, WIP), the work-station view (resource_id as work station, load and utilization), scheduled-vs-actual variance (setup/run hours and costs), outside-service operations, aerospace compliance angle (traceability, AS9100/FAA, inspection and NDT steps), the Knowledge Loop iteration section, shop-floor metrics, and an APICS mapping table.
2. **Author the grounding query.** Write a SQLite query that joins `work_order` and `operation` (two tables only), using `operation.resource_id` as the work station, surfacing routing sequence, operation status, and scheduled-vs-actual hours/costs. Target the SQLite `manufacturing.db` dialect per project convention.
3. **Verify the query.** Run it against `manufacturing.db` to confirm it returns meaningful rows; capture a small sample-output table to embed in the document.
4. **Embed and tie to the loop.** Place the query and its explained sample output inside the document, and write the "enabling Knowledge Loop iteration" section showing how actual execution data (actual vs estimated hours, completion timing, work-station load) feeds back to refine routing standards.
5. **Confirm no regressions.** Verify only the two new files are added (docs + SQL); no schema, graph, or app changes; existing gates remain green.

## Relevant files
- `docs/my-mrp-kb/Knowledge Loop Framework - Aerospace MRP.md`
- `docs/my-mrp-kb/kb-inventory-transactions/Inventory_-_Transactions_AI_Review.sqlite.sql`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql:210-293`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
