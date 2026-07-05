# SPARQL Constraints, "Not Elevate," and DBR Patterns

*Saved from chat — July 5, 2026*

A conversation thread on how SPARQL/OWL constraints open semantic doors for the palette-based
system, how "elevate" maps to standard RDF vocabulary (with a reverse and a true "not"), and
how Theory of Constraints patterns show up on the shop floor without formal DBR.

---

## 1. Constraints open the semantic door

The POC ontologies are deliberately minimal OWL 2 QL: classes, properties, labels, comments.
The standards stack has two natural next layers:

- **OWL restrictions** — statements like "every Operation must belong to exactly one WorkOrder"
  become machine-checkable, not just conventions buried in a JOIN.
- **SHACL shapes** — the RDF world's answer to the fail-closed philosophy. A shape can say
  "operationStatus must be Q, S, or C" or "runHours must be non-negative," and a validator
  flags every violation. Same spirit as the structural fingerprints and MRP input validation,
  expressed in a W3C standard any tool can enforce.

The POC already respects the constraint boundary in one place: the shop-floor ontology
deliberately omits `rdfs:domain` on `partOfWorkOrder` because a constraint there would make
Ontop emit bad SQL. Constraint-aware design is already happening — the next step is making
constraints a first-class, visible layer (a natural fourth tab under the one-concern-per-tab
structure).

**Why the palette works for supply chain**: the abstract and functional sides are *both
governed*. Every palette entry is an SME-approved query; every ontology term is bound to that
same SQL by a parity-checked mapping. SQL development stays in the loop because the SQL *is*
the ground truth — the ontology, the graph, and the SPARQL view are all governed windows onto it.

## 2. The SPARQL version of "elevate" — and its reverse

The RDF-world equivalents of the ELEVATES/RESOLVES_TO predicate:

- **`skos:broader` / `skos:narrower`** — the classic pair. `broader` points from a specific
  concept up to a more general one (the "elevate" direction: column → concept), and `narrower`
  is its built-in reverse. The ontology annotation work already uses SKOS (`skos:closeMatch`).
- **`owl:inverseOf`** — the general mechanism: declare `:resolvedBy owl:inverseOf :resolvesTo`
  and every triple works in both directions. In SPARQL the `^` operator walks any property
  backwards without needing the declaration: `?concept ^:resolvesTo ?column`.
- **`owl:NegativePropertyAssertion`** — the true "not elevate." A *constraint* stating "this
  column does NOT resolve to this concept" as a first-class, machine-checkable fact. Its cousin
  `owl:disjointWith` does the same for whole classes ("a Delivery is never a Supplier").

The design point: the graph currently encodes only positive knowledge (weight as a binary
gate). The RDF stack lets you encode *refusals* explicitly — "not elevate" as governed metadata
rather than silent absence. Absence of an edge means "nobody said anything"; a negative
assertion means "an SME explicitly ruled this out" — a different, stronger statement, and
exactly the fail-closed semantics the Solder Pattern favors. Supply-chain example: "this cost
column must never surface under the Customer perspective" as a stated rule instead of an
omission.

## 3. Theory of Constraints on the shop floor

A constrained resource may warrant top priority and overstock of materials in front of the
sequence, while non-constrained stations are subordinate to the bottleneck. The key insight:
**"constrained" is not a column.** Nothing in `shop_resource` or `operation` says which work
center is the bottleneck — it's SME knowledge, precisely what the ontology layer exists to
capture:

- **The drum** — one assertion (`:WC-300 a :ConstrainedResource`) names the bottleneck as
  governed metadata. One triple, SME-approved, reviewable like any other term.
- **The buffer** — "overstock in front of the constraint" inverts normal inventory logic.
  Everywhere else, excess stock is waste; in front of the drum, it's protection. Same physical
  quantity, opposite meaning depending on *where* it sits. Plain SQL can't tell those apart —
  a semantic layer can, because meaning comes from the work center's declared role, not the
  number.
- **The rope (subordination)** — non-constrained stations shouldn't be measured on their own
  efficiency; running them flat-out piles up WIP the drum can't swallow. This connects to
  "not elevate": a negative assertion like "utilization does NOT elevate to a performance
  concept at non-constrained stations" is a governed refusal. The metric exists, the SQL runs,
  but the layer says *this number is not meaningful here*.

Existing pieces already point at this: the capacity-planning showcase publishes work centers
and load per row ("load at the constrained resource vs. everywhere else" is one SPARQL filter
away once the drum is named), and the MRP tab's lot-for-lot planned orders are the textbook
baseline TOC deliberately violates in front of the bottleneck.

## 4. "We don't use DBR, but there are DBR patterns"

The shop doesn't formally run drum-buffer-rope, but the patterns emerge anyway: some station
sets the pace, material piles up in front of it on purpose, and efficiency numbers downstream
of it stop mattering.

That's the *stronger* argument for putting these in the ontology. Formal DBR would take its
vocabulary from the book; without it, the vocabulary has to come from the floor — which
station plays the pacing role this quarter, where buffering is intentional vs. accidental,
which metrics the planners already ignore and why. Observed, SME-attested patterns, not
framework doctrine — the same way the WO status vocabulary came from how the planners
actually work rather than from an ERP manual.

If this becomes a showcase, the terms would be pattern-shaped rather than DBR-branded: a
pacing-resource role, an intentional-buffer designation, a "this metric doesn't apply here"
refusal. Same semantics, grounded in what the data and planners actually do.

## Summary

| Layer | What it carries |
|---|---|
| SQL (ground truth) | The facts — quantities, statuses, loads |
| Ontology terms | The roles — drum, buffer, subordinate, pacing resource |
| Constraints (positive & negative) | The business judgment — what applies where, and what is explicitly refused |
