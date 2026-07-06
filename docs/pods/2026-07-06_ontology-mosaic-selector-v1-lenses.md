# Ontology Mosaic — Selector v 1.0 chain drives the three lenses

*Saved from chat, 2026-07-06.*

## What changed on the 🧩 Ontology Mosaic tab

- The old Category → Concept-anchor cascade is gone, replaced by the real
  **Selector v 1.0 chain** — the same filters as the 🎛️ Selector tab:
  Perspective filter → Table → Column → Concept → Intent → Ground-truth query.
- Picking a query now drives all three lenses:
  - **🔗 Join Topology** — extracted live by SQLGlot from the governed SQL
    (or from the seeded ontology when a query carries a binding marker)
  - **🧠 Semantic Ontology** — rendered from the concept picked in the chain
  - **📜 SQL** — the raw governed query text

## Verification

- App restarted cleanly; chain exercised end-to-end via the API —
  "AP Aging by Supplier" renders its summary, join table, and SQL correctly,
  and the semantic pane works with chain concept names.
- Code review passed; its one note (stale intro text describing the old
  cascade) was fixed too.

## Known gap (by design, next loop)

None of the 11 queries reachable through the chain carry a `-- Binding:`
marker yet, so today every lens renders through live SQLGlot extraction.
The seeded fast-path is in place and will kick in automatically once
bindings get wired to those queries.
