---
title: Selector v1.0 on Ontology Mapping tab
---
# Selector v1.0 on Ontology Mapping tab

## What & Why
Put the shared Selector v 1.0 pane (with its version stamp) at the top of the 🦉 Ontology Mapping tab — same placement pattern as the Ontology Mosaic tab — and drive the OBDA mapping display through the resolved binding key behind the scenes. Today the tab has its own two-dropdown picker (Category showcase ontology → OBDA mapping 6-slot), which is a separate selection vocabulary from the rest of the app. After this change, the SME picks the same way everywhere (Perspective filter → Table → Column → Concept → Intent → Ground-truth query), and the tab looks up which ontology mapping(s) belong to that governed query via its binding key — the key itself never shown in the UI.

## Done looks like
- The Ontology Mapping tab opens with the small "🎛️ Selector v 1.0" stamp and the same cascading selector row used on the Ontology Mosaic tab (max 5 dropdowns per row, narrow, concrete levels).
- Picking a ground-truth query shows the OBDA mapping(s) bound to it: summary, minted vocabulary, and the Target triples + source SQL accordion — same rendering as today.
- When the selected query has no ontology mapping bound, the tab says so plainly (fail visible, no silent fallback to an unrelated mapping).
- The binding-key → mapping bridge is explicit and governed (committed alongside the POC artifacts), not inferred fuzzily at runtime.
- Existing two-dropdown picker is removed (or demoted below as a browse-all fallback only if all mappings remain reachable through it).

## Out of scope
- No changes to the .obda/.ttl mapping content, parity checkers, or CI.
- No changes to the Ontology Mosaic tab or the 🎛️ Selector tab.
- No database writes; tab stays read-only.

## Steps
1. **Binding-key bridge** — Introduce an explicit link from manifest binding keys to OBDA mapping entries (an annotation the mapping loader parses, or a small committed bridge file in the POC), so each governed query resolves deterministically to zero or more mappings. Mappings whose source is a governed query must be linked; fail closed (report unbound) rather than guess by SQL similarity.
2. **Selector pane on top** — Mount the shared Selector v 1.0 cascade (same helpers and single-input packed-token handlers as the Mosaic tab, honoring the Gradio chained-.change rule) at the top of the Ontology Mapping tab with the version stamp above it.
3. **Behind-the-scenes resolution** — Wire the final query pick to resolve its binding key, look up the bridged mapping(s), and render them with the existing summary/vocabulary/target+source panes; show a clear "no ontology mapping bound to this query" message when the bridge returns nothing.
4. **Coverage note + verify** — Surface a small count of how many governed queries have bound mappings; verify in the running app that the pane order matches the Mosaic pattern and the payables/3WM chains resolve to their showcase mappings.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:6491-6560`
- `hf-space-inventory-sqlgen/app.py:6842-7007`
- `hf-space-inventory-sqlgen/ontop_ontology_selector.py`
- `hf-space-inventory-sqlgen/ground_truth_selector.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `poc/ontop-ontology-poc/mapping/three_way_match.obda`
- `docs/pods/2026-07-06_selector-v1-ontology-mosaic-top.md`