---
title: Field descriptions for graph columns
---
# Field Descriptions for Graph Columns

## What & Why
The 223 columns that appear as column nodes in the canonical semantic graph mostly lack plain-language field descriptions — only 14 are written today, leaving ~209 blank. These descriptions power the Schema Browser overlay and the SolderEngine's per-column explanations, giving analysts (and the orchestrator's routing context) a clear, business-meaningful sense of what each field means. This task fills in the missing descriptions so every canonical-graph column is described.

Descriptions stay in the overlay store only (`api_field_descriptions`) — they are deliberately NOT written onto the graph's column nodes. This protects the dual-namespace boundary: physical column nodes stay purely structural, while all business meaning lives on the abstract Concept nodes. Putting descriptions on physical columns risks the LLM orchestrator bypassing RESOLVES_TO routing and being confused by duplicated semantic data.

## Done looks like
- Every one of the 223 canonical-graph columns has a display name + plain-language description in the overlay, visible in the Schema Browser and in solder reports.
- The descriptions live in a committed, version-controlled, SME-editable source so they survive a database rebuild (not only in the gitignored WAL database).
- `graph_metadata.json` and the live graph are unchanged — no descriptions on any column node; node/edge counts identical (289 / 282 / 20).
- A coverage check confirms 223/223 canonical columns are described, and the post-merge test gate stays green.
- Drafts are generated AI-assisted (small `gpt-4o-mini` spend) with automatic deterministic fallback whenever the key is missing or a call fails.

## Out of scope
- Describing non-graph columns (the other ~190), staging (`stg_`) columns, or infra/metadata tables.
- Writing any description onto graph column nodes, or regenerating / reloading the graph.
- SME certification into `dab_field_definitions` — that remains a later human step; this task only populates the overlay drafts.
- Adding synonyms or business definitions to Concept nodes (separate concept-layer work).

## Steps
1. **Pin the target column set** — Derive the exact list of columns that appear as column nodes in the canonical graph, subtract those already described, and produce the missing set (~209) to fill.
2. **Teach the drafter to use the guide/KB as needed** — Extend the AI-assisted draft path so it can pull relevant knowledge-base / guide context (e.g. the MRP/inventory knowledge base and the integration guide) into the prompt selectively per column, keeping prompt size and cost down. The deterministic fallback path stays unchanged.
3. **Generate drafts for the missing columns** — Run the drafter over the target set using the AI path with deterministic fallback, producing a display name, description, and example value for each column.
4. **Persist to a committed, SME-editable source** — Record the authored descriptions in a version-controlled manifest/data file so re-seeding restores them after any database rebuild; the boot seed upserts them into the overlay table.
5. **Guardrail: keep the graph pure** — Verify that no description is written to any graph column node and that `graph_metadata.json` plus the node/edge counts are byte-for-byte unchanged.
6. **Coverage + tests** — Add a check that all 223 canonical columns are covered, confirm the overlay surfaces them in the Schema Browser and solder report, and keep the post-merge gate green.

Architectural constraint: descriptions belong only to the overlay namespace (`api_field_descriptions`), never to the structural column nodes. AI spend is one-time (authoring the committed source), not per-boot, and the deterministic fallback guarantees the pipeline never hard-fails.

## Relevant files
- `hf-space-inventory-sqlgen/field_description_pipeline.py`
- `replit_integrations/seed_field_descriptions.py`
- `hf-space-inventory-sqlgen/app.py:585-695`
- `hf-space-inventory-sqlgen/solder_engine.py:621-666`
- `replit_integrations/graph_metadata.json`
- `hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py`
- `docs/mrp_inventory_knowledge_base.md`
- `define-relationship-integration-guide.md`