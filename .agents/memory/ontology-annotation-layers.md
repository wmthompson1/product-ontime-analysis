---
name: Ontop ontology annotation layers
description: How to safely add Layer B/C curation annotations to the POC .ttl ontologies without tripping the drift/generation gates.
---

# Curating the Ontop POC ontologies (`poc/ontop-ontology-poc/ontology/*.ttl`)

## The gates are regex parsers, not RDF parsers
`mapping_drift_check.py` and `mapping_generation_check.py` parse the `.ttl` with a
hand-rolled regex parser (deliberately *no* rdflib dependency). They only "see":
- `a owl:Class` / `a owl:(Object|Datatype)Property` declarations (the declared-term set),
- `rdfs:subPropertyOf :LocalTerm` (only when the parent is a `:`-prefixed local term),
- `.obda` byte-equivalence + mapping↔ontology vocabulary closure.

Everything else — `skos:definition`, `skos:scopeNote`, `rdfs:comment`,
`rdfs:isDefinedBy`, and structural relations whose **object is an external IRI**
(`rdfs:subClassOf schema:Order`, `rdfs:subPropertyOf schema:name`) — is invisible
to the gates. So enriching **already-declared** terms with annotation layers does
not change the declared-term count and keeps both gates green.

## Conventions
- **Only annotate terms that already exist** and are already backed by an `.obda`
  mapping. A brand-new `:Term a owl:Class` with no mapping fails drift's
  ontology→mapping closure. New *mapped* terms (e.g. payable / 3-way-match) need
  generator + parity work first and depend on the private SQL Server schema.
- **Layer C alignment: use `rdfs:subClassOf` / `rdfs:subPropertyOf` (specialization)
  and `skos:closeMatch` (crosswalk) — NOT `owl:equivalentClass`/`equivalentProperty`.**
  **Why:** equivalence over-claims (`:Supplier ≡ schema:Organization` would assert
  every Organization is a Supplier). External targets carry no `.obda` mappings, so
  these axioms are documentation-only and don't change Ontop's query rewriting over
  governed data.
- Keep `.obda` source SQL and `generate_mapping.py` untouched for a pure annotation
  pass — that's what makes it provably data-neutral.

## Zero-weight (owl:complementOf) enforcement contract
The `wgt:` weight namespace is enforced, not just documented. A term typed
`a wgt:ZeroSemanticWeightContext` (complement of the elevated ledger-fact set)
carries a machine-readable `wgt:physicalColumn "table.column"` pointer. The
fail-closed gate (`test_zero_weight_fields_have_no_resolves_to_edge` in
`hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py`, registered
in `post-merge.sh`) resolves that column to the canonical node key
`table:column:structural:system:none:none` and asserts it is NEVER the `_from` of
a `resolves_to` edge in both `graph_metadata.json` and SQLite `sql_graph_edges`.
**Why:** the complementOf rule only *declared* zero weight; nothing stopped a graph
change from silently elevating the field. **How to apply:** when you flag a new
zero-weight field, add the `wgt:physicalColumn` annotation too, or the gate can't
verify it (it fails closed on an unresolvable flag).

## Validation without adding a dependency
rdflib is intentionally NOT a committed dependency. Validate Turtle as a throwaway:
`uv pip install rdflib` → `Graph().parse(f, format="turtle")` → `uv pip uninstall rdflib`.
Never make committed code import rdflib.
