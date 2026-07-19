# Load SKOS Concepts from JSON-LD

## What & Why
Establish the ontology backbone: commit the drafted SKOS JSON-LD (ledger/job-costing concepts: RawMaterialsInventory, WIPInventory, FinishedGoodsInventory, JobCostDetail, and the event vocabulary) into the repo, load it at startup, hold the concepts in memory, and expose them to the semantic layer. Note: no JSON-LD file exists in the repo today — the user's drafted JSON-LD must be requested from the user or faithfully authored from the PM plan as step one.

## Done looks like
- A committed JSON-LD file (e.g. under the Ontop POC ontology folder or a new `ontology/` location consistent with repo layout) containing the SKOS concept scheme with prefLabels, definitions, and broader/narrower structure.
- Optional raw-material subtypes (standards, detail parts, components, sheet metal) included as `skos:narrower` concepts under Raw Materials — included since it is cheap here (folds in PM Task 8).
- A small loader module parses the JSON-LD, exposes concepts in memory with lookup by label/URI, and fails closed on malformed input.
- A read-only accessor makes the loaded concepts available to the app/semantic layer (queryable list of concepts with labels and relations).
- Gate-style test proving load, lookup, and hierarchy traversal.

## Out of scope
- RDF event classes and flow properties (Task 4).
- Binding concepts to tables (Task 6).

## Steps
1. **Obtain/author the JSON-LD** — ask the user for their drafted JSON-LD; if unavailable, author it from the PM plan's concept list and get the shape confirmed.
2. **Loader module** — parse, validate, in-memory concept store with lookups.
3. **Exposure + test** — accessor for the semantic layer and a gate-style test.

## Relevant files
- `poc/ontop-ontology-poc/ontology/`
- `poc/ontop-ontology-poc/README.md`
- `docs/pods/2026-07-05_sparql-constraints-dbr-patterns.md`
