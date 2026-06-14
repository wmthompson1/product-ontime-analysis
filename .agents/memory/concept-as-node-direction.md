---
name: Concept-as-node direction
description: Active design decision to add Concept as a 3rd graph node, departing from the two-node-type invariant; where the canonical spec lives and what gates it.
---

# Concept-as-node direction (Option C)

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
- **Built through M2 (SCHEMA_VERSION 14).** The graph now has THREE node types, so
  the old two-node-type invariant in `solder-pattern-architecture.md` no longer
  describes what *exists* — concept nodes are real. M1 added identity-only concept
  nodes (v13); M2 re-pointed `ELEVATES` to `column → concept` and dropped the edge
  `concept` string (detail in `semantic-elevates-scaffolding.md`). M3 (richer
  concept payload: type / domain / synonyms / tags) is the next milestone, not yet
  built.
- All three Pre-M1 gates are CLOSED: B1 (concept `_key` grammar, see
  `composite-key-scheme.md`); B2 (no shadow graph was needed — no live consumer
  reads the canonical edges, so safety is freeze-once `vN` + both parity gates +
  rollback to the prior `vN`; live load is truncate-then-import on the canonical
  collections only); B3 (`priority_weight` → binary `weight`).
- The HF app still reads the LEGACY named graph, so concept nodes + re-pointed
  edges are inert there (resolvers filter `node_type` to table/column).
