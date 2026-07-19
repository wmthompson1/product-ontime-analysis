# GL (Job-Costing Ledger) Ontology — Status

*Saved 2026-07-19. All gates green as of the full 52-gate post-merge run on this date.*

Here's the current state of the GL (job-costing ledger) ontology, layer by layer — it's fully built out and all gates are green as of the run we just completed:

**Physical layer (SQLite):** Five `gl_*` sub-ledger tables — `gl_events` (the audit trail), `gl_job_cost_detail`, and the three perpetual inventory buckets (`gl_raw_materials_inventory`, `gl_wip_inventory`, `gl_finished_goods_inventory`). The ledger is backfilled deterministically from work-order actuals, and a gate proves `gl_job_cost_detail` ties out to those actuals with balanced, idempotent postings.

**Concept layer (SKOS):** The "Job-Costing Ledger Concept Scheme" loads at boot — 13 concepts, 5 top-level. Each of the 5 gl_* tables is bound to its SKOS concept exactly once, and each of the 4 posting event types is bound to its OWL event class exactly once, via the committed binding map. A dedicated gate fails closed on any inconsistency.

**Event ontology (OWL):** `ledger_events.ttl` declares the four posting event classes with their flow properties, linked into the SKOS scheme via `skos:closeMatch` only (never `owl:equivalentClass`, per the annotation-layer rules). There's also a Job lifecycle model — `:Job` with four state individuals matching the real work-order status vocabulary — with fail-closed lifecycle functions.

**RDF event trace:** Every ledger posting is expressible as RDF triples with deterministic IRIs, gated 1:1 against `gl_job_cost_detail` on the live database.

**SPARQL publication (Ontop POC):** The gl_* tables are published over SPARQL via `job_costing_ledger.obda` + `job_costing_ledger.ttl`, with generation-equivalence and drift gates proving the mapping stays byte-aligned with the governed schema.

**Query/mosaic layer (new as of Task #278):** The 5 governed ledger queries are approved snippets with v2 fingerprints, routable through the NLQ layer, and now surfaced in the ontology mosaic — 4 time-phased (bounded date windows) and the inventory balance as point-in-time, with their `gl_*` table usage indexed for the selector.

The one known gap is unchanged: the live ArangoDB graph is still on the legacy key model, so the SQL↔AQL parity check warns — documented out of scope, non-fatal.
