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
- Not built yet — current code/graph still has two node types, so
  `solder-pattern-architecture.md` is still accurate for what *exists*. When you
  actually implement, update that memory in lockstep.
- Three Pre-M1 blocking gates must close first: concept `_key` grammar under the
  6-slot scheme (B1), shadow-graph cutover + rollback to v12 (B2), and
  priority_weight → binary `weight` normalization (B3).
- `ELEVATES` changes from a column self-loop carrying a `concept` string to a
  `column → concept` edge; build in shadow collections, switch readers atomically.
