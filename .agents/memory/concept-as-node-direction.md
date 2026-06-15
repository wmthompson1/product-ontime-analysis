---
name: Concept-as-node direction
description: Active design decision to add Concept as a 3rd graph node, departing from the two-node-type invariant; where the canonical spec lives and what gates it.
---

# Concept-as-node direction (Option C)

**v16 rename:** the canonical column→concept predicate `elevates`/`ELEVATES` was
renamed `resolves_to`/`RESOLVES_TO` (uid `ELE`→`RES`); references below use the
pre-v16 name. (The legacy Model-A `elevates` Arango collection is untouched.)

The semantic layer is moving to add **Concept as a first-class graph node** (a
third node type alongside tables + columns). This is a *deliberate, ratified
departure* from the long-standing "graph has only table + column nodes"
invariant recorded in `solder-pattern-architecture.md`.

**Why:** richer traversal (column → concept → sibling columns) and a first-class
home for each concept's synonyms / definition / domain / tags. The architect
strongly advocated it; the user accepted the loss of two-node-type purity. Tags
are settled as a *lightweight filter only* (no meaning, AQL prefilter).

**How to apply:**
- The canonical, *living* spec is `docs/canonical_graph_construction_concept_as_node.md`
  (revision header + Open Questions + Decision Log; iterate it, don't fork it).
- **Built through M3 (SCHEMA_VERSION 15).** The graph now has THREE node types, so
  the old two-node-type invariant in `solder-pattern-architecture.md` no longer
  describes what *exists* — concept nodes are real. M1 added identity-only concept
  nodes (v13); M2 re-pointed `ELEVATES` to `column → concept` and dropped the edge
  `concept` string (detail in `semantic-elevates-scaffolding.md`); M3 added the
  richer concept payload (`concept_type` / `domain` / `synonyms[]` / `tags[]`) and
  seeded the MRP/inventory vocabulary. M4 (AQL resolution + private-repo routing
  agent) is the next milestone, not yet built.
- **Concepts are perspective-AGNOSTIC nodes; perspective lives only on the `elevates`
  edge (dual-namespace).** Never stamp a perspective on a concept node — this
  resolved the spec's Open Question 1. A concept (`ReorderPoint`) is one canonical
  thing; the lens-specific reading of a column lives on the edge.
- **The ontology may hold a term before the warehouse has the column.** M3 seeded
  ALL 10 MRP terms as concept nodes but only the 3 with a real column got `elevates`
  edges; the other 7 are intentional **orphan glossary nodes** (edgeless until ETL
  onboards a column). So a concept node with no edge is by-design, not drift.
- **Watch the seed insert column-order.** `seed_elevations.py` concept inserts must
  match `(name, concept_type, description, domain, synonyms, tags)`; a value-tuple
  in the wrong order silently swaps `description`↔`domain` and survives every parity
  gate (parity only checks SQLite↔file↔AQL agree, not that the *content* is sane).
- All three Pre-M1 gates are CLOSED: B1 (concept `_key` grammar, see
  `composite-key-scheme.md`); B2 (no shadow graph was needed — no live consumer
  reads the canonical edges, so safety is freeze-once `vN` + both parity gates +
  rollback to the prior `vN`; live load is truncate-then-import on the canonical
  collections only); B3 (`priority_weight` → binary `weight`).
- The HF app still reads the LEGACY named graph, so concept nodes + re-pointed
  edges are inert there (resolvers filter `node_type` to table/column).
