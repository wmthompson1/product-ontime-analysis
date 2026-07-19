# RDF Event Classes & Flow Properties

## What & Why
Define the RDF layer that lets the semantic layer reason about job-costing flow: event classes `MaterialIssueEvent`, `LaborApplicationEvent`, `OverheadApplicationEvent`, `JobCompletionEvent`, and flow properties `consumesMaterial`, `addsCostToWIP`, `producesFinishedGoods`, plus `forJob`. Delivered as a Turtle/JSON-LD ontology file consistent with the existing Ontop POC ontology conventions.

## Done looks like
- A committed ontology file declaring the four event classes and the flow properties with domains/ranges tying events to the SKOS inventory concepts (MaterialIssueEvent consumesMaterial RawMaterialsInventory, addsCostToWIP WIPInventory; JobCompletionEvent producesFinishedGoods FinishedGoodsInventory; every event forJob a Job).
- Follows the safe-annotation conventions already established for the POC ontologies: enrich with `rdfs:subClassOf`/`skos:closeMatch`, never `owl:equivalentClass`; no unmapped free-floating terms beyond the declared set.
- The ontology loads cleanly alongside the existing `.ttl` files (a load/validation script or existing POC check passes).
- A short vocabulary reference section added to the POC README.

## Out of scope
- Emitting event instances from posting functions (Task 5).
- SPARQL mappings to the ledger tables (Task 6).

## Steps
1. **Author the ontology file** — classes + properties with domains/ranges referencing the SKOS scheme from the JSON-LD task.
2. **Validation** — parse/consistency check via the POC tooling pattern; ensure existing POC checks still pass.
3. **Document** — vocabulary summary in the POC README.

## Relevant files
- `poc/ontop-ontology-poc/ontology/three_way_match.ttl`
- `poc/ontop-ontology-poc/README.md`
- `docs/pods/2026-07-05_sparql-constraints-dbr-patterns.md`
