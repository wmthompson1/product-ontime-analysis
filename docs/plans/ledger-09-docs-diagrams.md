# Ledger Documentation & Ontology Diagrams

## What & Why
Final deliverable: documentation tying the whole ledger build together — ontology diagram, job-costing flow diagram, JSON-LD reference, and posting-model reference — so an SME or future agent can understand the system without reading code.

## Done looks like
- A docs folder section (consistent with existing `docs/` conventions) containing: (1) ontology diagram showing SKOS concepts, RDF event classes, and flow properties; (2) job-costing flow diagram (material → WIP → finished goods with event annotations); (3) JSON-LD reference documenting every concept with label and definition; (4) posting-model reference documenting the four functions, their table effects, idempotency keys, and the no-control-logic design decision.
- Diagrams generated deterministically (e.g. Graphviz source committed alongside rendered output) so they can be regenerated when the ontology changes.
- A short index page linking the four artifacts and stating the simplified-GL design rationale.

## Out of scope
- Any code or ontology changes; documentation only.
- User-facing UI help text.

## Steps
1. **Diagrams** — author Graphviz (or equivalent committed-source) diagrams for ontology and flow from the merged ontology files.
2. **References** — JSON-LD concept reference and posting-model reference derived from the merged code and ontology.
3. **Index** — single entry page in docs linking all artifacts.

## Relevant files
- `docs/mrp_graph_topology_blueprint.md`
- `poc/ontop-ontology-poc/README.md`
- `docs/my-mrp-kb/01-core-framework/Manufacturing and MRP Terminology in Semantic Models.md`
