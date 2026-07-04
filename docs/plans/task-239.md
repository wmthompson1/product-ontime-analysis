---
title: Blueprint the graph-topology alternative for the 7 MRP concepts (decision-support, no code)
---
# MRP Graph-Topology Blueprint (decision-support)

## What & Why
The merged set-semantics criteria (Task #237, `docs/mrp_set_semantics_criteria.md`) concluded that all 7 MRP/inventory concepts (AllocatedQuantity, AvailableToPromise, LeadTimeDemand, SafetyStock, MinimumStockQuantity, MaximumStockQuantity, EconomicOrderQuantity) should stay **pure-SQL** and make **no ArangoDB graph change**. That recommendation is currently taken on faith. Before the project either commits to pure-SQL for good or pivots part of it into graph topology, we need a rigorous, written **blueprint** that lays out exactly what a true canonical-graph-path implementation — plus its Ontop/SPARQL and SQLGlot parity consequences — would look like for these specific 7 concepts.

This is **intelligence-gathering only**. It changes no code, no manifest, no snippets, no graph, no `.obda`/`.ttl` files, and no `graph_metadata.json`. Its single deliverable is one architect/SME-reviewable document that gives a clean, evidence-based blueprint so the team can deliberately choose "stick with pure-SQL window/set functions" vs. "execute a formal pivot to graph topology" — and understand whether SPARQL/SQLGlot integration lands on the critical path — **without derailing the in-flight #238 authoring sprint**.

This task does not block #238 and #238 does not block it; they run in parallel. #238 continues authoring pure-SQL snippets per the approved criteria; this task documents the road-not-taken so a future decision is informed rather than reflexive.

## Done looks like
- A single reviewable blueprint document exists (`docs/mrp_graph_topology_blueprint.md`) covering all 7 concepts.
- The document **re-examines #237's SQL-only claim per concept** and states, with evidence, where graph topology could add real value (navigation/interoperability) and — critically — where the graph provably *cannot* carry the logic (row-level state predicates and time-phased bucket arithmetic), so the reader can see the boundary rather than take it on faith.
- For each concept it specifies, **hypothetically**, the set-topology edge(s) that would model it in the canonical graph: the predicate/edge-type name, `_from`/`_to` node kinds, cardinality, any edge properties, and how it would fit the fixed 6-slot composite `_key` scheme and reserved-token rules — flagging any concept whose relationship spans two table endpoints (e.g. demand→supply) because of the two-endpoint prune handling.
- It documents the **full canonical graph path** end-to-end as it would apply here: seeding edges (the `seed_elevations.py`-style manifest), re-export via `export_graph_metadata.py` (new edge rows/ordinal in `sql_graph_nodes`/`sql_graph_edges`), the SCHEMA_VERSION bump + frozen `graph_metadata.v{N}.json` snapshot, the live resync via `load_canonical_to_arango.py`, and both parity gates (`sql_graph_parity_check.py` file-vs-SQLite and `sql_aql_parity_check.py` SQLite-vs-live-AQL), including the shared-cloud-ArangoDB parity-race caveat and which gate is the real acceptance.
- It maps the **Ontop/SPARQL parity dimension**: which new `.obda` mappings and `.ttl` ontology terms each concept would need to be republished as a virtual OWL/SPARQL graph, whether each is expressible in OWL 2 QL / SPARQL, the known Ontop+SQLite serialization limits (single-triple OPTIONAL, SUM/COUNT+COALESCE vs. NULL-drop, the ATP scalar-split gotcha), the SQLGlot "lift" needed for nested LEFT JOINs, and how a new parity checker + `ontop-interop-ci.yml` step would be added.
- It assesses the **SQLGlot dimension**: whether these concepts are better served as plain approved snippets or promoted to M4 `computation_template` metrics (define-once → identical SQL, cross-dialect transpile), and the multi-dialect implications of each surface choice.
- It ends with a **per-concept decision matrix** (pure-SQL vs. canonical-graph-topology vs. M4-metric-template) with cost/benefit, a recommendation, and an explicit **critical-path verdict**: does adopting graph topology for any concept force SPARQL/SQLGlot work to complete before the current iteration can ship, or can it be deferred?
- The document is explicit that it is a blueprint: no code, manifest, snippet, graph, `.obda`/`.ttl`, or `graph_metadata.json` changes are made by this task.

## Out of scope
- Implementing any of it: no edges added, no `graph_metadata.json`/SCHEMA_VERSION change, no `load_canonical_to_arango.py` run, no `.obda`/`.ttl` authoring, no new parity checker or CI step, no snippet/manifest edits.
- Redefining the set semantics themselves (that is the merged #237 deliverable; this task takes those definitions as given).
- Any change to the #238 authoring work, which proceeds independently in pure-SQL per the approved criteria.
- Adding new physical columns to the synthetic schema.

## Steps
1. **Restate the baseline and the boundary** — Summarize #237's per-concept SQL-only recommendation, then test it: for each of the 7 concepts, classify its logic as (a) routing/navigation the graph can carry, (b) row-level state predicate the graph cannot, or (c) time-phased bucket arithmetic the graph cannot — with concrete reasons per concept.
2. **Design the hypothetical edges** — For each concept where graph topology is even conceivable, specify the candidate set-topology edge(s): predicate name, `_from`/`_to` node kinds, cardinality, edge properties, fit to the fixed 6-slot `_key` scheme and reserved-token rules, and whether the edge spans two table endpoints (two-endpoint prune implication).
3. **Document the canonical graph path** — Lay out the exact end-to-end mechanics these edges would travel (seed → export/materialize into `sql_graph_*` → SCHEMA_VERSION bump + freeze snapshot → live resync → both parity gates), calling out the frozen-once snapshot cost, the shared-cloud live-graph parity race, and which gate is authoritative.
4. **Map the Ontop/SPARQL + SQLGlot consequences** — For each concept, specify the `.obda`/`.ttl` additions, OWL/SPARQL expressibility, Ontop+SQLite serialization limits and the SQLGlot lift, plus the new parity-checker + CI wiring; and separately assess plain-snippet vs. M4 `computation_template` metric and its cross-dialect impact.
5. **Write the decision matrix and critical-path verdict** — Produce the per-concept pure-SQL vs. graph-topology vs. metric-template matrix with cost/benefit and a recommendation, and state plainly whether any graph-topology choice pulls SPARQL/SQLGlot onto the critical path for the current iteration or can be safely deferred. Capture everything in `docs/mrp_graph_topology_blueprint.md`.

## Relevant files
- `docs/mrp_set_semantics_criteria.md`
- `docs/mrp_inventory_knowledge_base.md`
- `docs/canonical_graph_construction_concept_as_node.md`
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/seed_elevations.py`
- `replit_integrations/load_canonical_to_arango.py`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/mrp_engine.py`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `poc/ontop-ontology-poc/mapping/`
- `poc/ontop-ontology-poc/ontology/`
- `poc/ontop-ontology-poc/sql_lift.py`
- `poc/ontop-ontology-poc/rating_parity_check.py`
- `poc/ontop-ontology-poc/mapping_drift_check.py`
- `.github/workflows/ontop-interop-ci.yml`
- `scripts/post-merge.sh`