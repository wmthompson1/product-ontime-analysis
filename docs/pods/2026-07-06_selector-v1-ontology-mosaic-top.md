# Selector v 1.0 — pane moved to the top of the Ontology Mosaic tab

*Saved from chat, 2026-07-06.*

## Final placement

The selector pane now sits at the top of the **🧩 Ontology Mosaic** tab:

1. **🎛️ Selector v 1.0** stamp (small bold print) first
2. Then the cascading selector — Category → Concept anchor → Query, with the Show button
3. Then the "three lenses" intro text below it
4. Then the Join Topology / Semantic Ontology / SQL lens tabs

The stamp was also removed from the top of the page (that earlier placement was wrong). Verified in the running app that the components render in exactly that order.

## Context — how we got here (same session)

- **Selector v 1.0 behavior** (🎛️ Selector tab, first tab): picking a Table auto-selects **"(all columns)"** and fills Concepts immediately; picking a Concept pre-selects an **"(any intent)"** wildcard that lists every query reachable from the concept. Practical flow is now **Tags → Table → Concept → Query** — Column and Intent are refinements, not required stops.
- Verified end-to-end on the payables chain: `Payables` → `payables` → ThreeWayMatchState → 3 queries under the wildcard ("AP Aging by Supplier", "Supplier AP Total Due", "Three-Way Match Exceptions"), same list narrowed correctly under the explicit intent.
- The version stamp went through three placements (inside the Selector tab → top of the page → **top of the Ontology Mosaic tab**), landing on the last per user direction, anchored to the mosaic's shared cascading selector so version drift is obvious where it matters.
