---
title: Ontology Mosaic: 3 tabs, one cascading selector
---
# Ontology Mosaic: 3 Tabs, One Cascading Selector

## What & Why
Build the **Ontology Mosaic** as **three tabs** in the Gradio app, all driven by **one shared selector**:

1. **Graph join topology** — the SQLGlot-extracted view ontology (tables touched, join relationships, set-membership predicates, grain, time-phasing) that the current Query Topology tab renders.
2. **Semantic ontology** — the concept-layer story for the same anchor: concept node, `resolves_to` variable→column→table lineage, computation template (when the concept is a metric), and perspective, read from the governed `sql_graph_nodes` / `sql_graph_edges` tables (read-only; frozen `graph_metadata.json` untouched).
3. **SQL** — the raw approved ground-truth SQL text.

The **shared selector cascades from Category**: Category → Concept anchor → Query/perspective (auto-hidden or auto-selected when only one match). It is populated from the reviewer manifest's `category` field (near-duplicate raw labels like `Quality` vs `quality_control` merged for display only — the manifest is never edited). All three tabs stay in sync: picking an anchor once selects it everywhere.

**Design the selector as a reusable component, not tab-local wiring.** It will grow:
- more filters will be added going forward (the cascade is filter #1);
- it may later be reused as a segment selector for an ontology mosaic of **metrics**.
So its state (current filters + resolved selection) and its choice-loading logic must live in one module with a clean interface the tabs subscribe to, so a future filter or a second consumer (metrics mosaic) plugs in without rewiring the tabs.

Everything stays pure AST + governed metadata: nothing is executed against a database.

## Done looks like
- Three tabs (Join Topology, Semantic Ontology, SQL) exist, each rendering its pane for the currently selected anchor.
- One selector — Category dropdown, then Concept anchor, then Query/perspective — appears consistently on all three tabs, and a selection made on any tab is reflected on the others.
- Categories show clean human labels; anchors show the concept + table list style from today (e.g. `SAFETYSTOCK [part, customer_order_line, …]`); the final level keeps the 6-slot summary labels for orientation.
- Concepts with no semantic-layer presence degrade gracefully in the Semantic Ontology tab (clear message, no error).
- The selector module has an obvious seam for adding future filters and for reuse by a metrics mosaic (documented in the module docstring), without any tab code changes required for a new filter's plumbing.
- Existing flat-selector behavior survives as a fallback if the manifest lacks categories; no existing tests or parity gates regress.

## Out of scope
- Building any additional filters now (only the Category cascade ships; the seam for more is what ships with it).
- The metrics ontology mosaic itself (future consumer; only the reusability seam is in scope).
- Writing to graph tables, `graph_metadata.json`, or the manifest.
- ArangoDB live graph/sync; the Ontop/OWL Ontology Mapping tab; React/canvas mockups.

## Steps
1. **Shared selector module** — Extend the ground-truth selector loader into a reusable component: normalized category → anchor → query choice model, cascade-resolution logic, and a single selection state the tabs consume; document the extension seam for future filters and the metrics-mosaic reuse.
2. **Three tabs, one selector** — Restructure the current Query Topology surface into the three mosaic tabs, each mounting the shared selector and staying synchronized on selection.
3. **Join Topology tab** — Reuse the existing view-ontology extraction/rendering behind the new selector.
4. **Semantic Ontology tab** — Read-only renderer pulling concept node, `resolves_to` lineage, and computation template from the SQLite `sql_graph_*` tables (reusing Metrics tab lineage logic where practical), with graceful degradation.
5. **SQL tab** — Raw ground-truth SQL display for the resolved query.
6. **Tests + gates** — Tests for the cascade model (category normalization/grouping, anchor filtering, single-match resolution, selection-state sync) and the semantic-ontology renderer; wire into `scripts/post-merge.sh`; verify all three tabs end-to-end in the running app.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:5919-6115`
- `hf-space-inventory-sqlgen/ground_truth_selector.py`
- `hf-space-inventory-sqlgen/view_ontology_extractor.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `scripts/post-merge.sh`