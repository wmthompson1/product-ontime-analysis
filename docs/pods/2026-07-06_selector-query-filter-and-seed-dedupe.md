# Selector tab — ground-truth query field as live filter + seed dedupe fix

*Saved from chat, 2026-07-06.*

Here's what was actually going on with the empty Ground-truth query field — two separate problems:

**1. The dropdown only filled after a full drill-down.** You think of the five fields as filters, but the query field only populated after picking Table → Column → Concept → Intent. Now it works as a live filter: it shows every reachable query from the moment the page loads, narrows as you pick tags or drill into the chain, and you can pick a query directly at any point.

**2. A real data bug was hiding the picture.** The intent→query link table had 286 rows but only 6 real mappings — the seed file re-runs on every app restart and was silently duplicating its 5 rows each time (57 restarts → 286 rows). The seed now dedupes itself (idempotent self-heal DELETE + unique index on `intent_id, query_file, query_index` + `INSERT OR IGNORE`) and can never duplicate again; the table is back to 6 clean rows. Every other seeded table was verified duplicate-free.

What you'll see after a refresh:

- **No tags:** 5 ground-truth queries listed immediately (Defects by severity, Weekly defect rate trend, Customer escape risk, Supplier delivery scorecard, Late delivery penalty).
- **Finance tag:** narrows to "Late delivery penalty calculation".
- **Quality tag:** narrows to scorecard + defect trend.
- **Inventory tags:** still honestly zero — no inventory SQL has been wired into the ground-truth library yet, and the panel says so up front.

One gap worth knowing about: the "Supplier AP exposure" query exists but its intent (`supplier_payables_exposure`) was never linked to any concept in the semantic layer, so it can't be reached through the chain. That's an SME wiring decision — it stays unreachable until a concept link (e.g. PayablesExposure) is added to `schema_intent_concepts`.

## Related earlier fix (same session)

The "zero ground-truth queries" symptom also had a filtering cause: the intent-level perspective filter double-filtered chains. `schema_intent_perspectives` is sparse (17 rows), so perspectives like Finance — whose concepts elevate to query-bearing intents — showed zero queries. Tags now filter tables/concepts via `schema_perspective_concepts` but no longer filter intents, and the Selection context panel shows "Ground-truth query coverage: N queries reachable" the moment tags are picked, with an honest warning (and a live-computed list of covered perspectives) when the count is zero.
