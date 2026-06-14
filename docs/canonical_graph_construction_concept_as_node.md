# Canonical Graph Construction — Concept as a Node

> **Status:** DRAFT — living document (canonical-in-progress)
> **Revision:** 0.2
> **Last updated:** 2026-06-14
> **Baseline graph:** `graph_metadata.v12.json` (`SCHEMA_VERSION = 12`, two node types)
> **Target milestone:** first concept-as-node snapshot (next `SCHEMA_VERSION` bump)

This is the canonical reference for how the manufacturing semantic-layer graph is
constructed once **Concept becomes a first-class node** (Option C). It is written
to be *iterated*: design discussions cause drift, so unresolved items live in
[§ Open Questions](#open-questions) and every ratified change is recorded in the
[§ Decision Log](#decision-log) with a revision bump. Do not treat any section as
final until its open questions are closed.

---

## How to use this document (iterative protocol)

1. **The graph is built from SQLite, then frozen.** SQLite (`schema_*` tables) is
   the source of truth. The exporter serializes it to `graph_metadata.json` and
   freezes a create-once snapshot `graph_metadata.v{N}.json`; the loader pushes it
   to ArangoDB. Each spec milestone maps to one `SCHEMA_VERSION` bump.
2. **Drift has a home.** When a discussion changes direction, add/adjust an entry
   in [§ Open Questions](#open-questions). When it is settled, move the resolution
   into the body **and** append a [§ Decision Log](#decision-log) line, then bump
   the Revision in the header. The spec never silently contradicts itself.
3. **One change per snapshot.** Prefer small, verifiable milestones (a new node
   type, then re-pointed edges, then metadata) over a big-bang rewrite — each is a
   frozen `v{N}` you can diff and roll back to.

---

## 0. Pre-M1 blocking decisions (must close before any construction)

Per architect review (Rev 0.2), these are **gates**, not open musings — M1 cannot
start until each is resolved and recorded in the Decision Log:

- **B1 — Concept `_key` grammar.** The current 6-slot parser classifies any node
  with `slot[4:6]==none` and `slot[1] != entity` as a *column*. A `concepts` node
  cannot be added until the key grammar, reserved tokens, the `node_type` enum,
  the parser rules, the SQL table CHECK constraints, and the parity flatteners all
  explicitly admit `concept`. This is a schema-design blocker, not a detail.
- **B2 — Shadow-graph cutover + rollback.** Re-pointing `ELEVATES` in place would
  break the running HF Space and any consumer expecting self-loop edges with a
  `concept` string. Construction must build vNext in **isolated collections / a
  versioned graph**, pass SQL↔file + SQL↔AQL parity and app-compatibility checks,
  then switch readers atomically, with a documented rollback to `v12`.
- **B3 — Weight normalization.** `schema_perspective_concepts.priority_weight` is
  not the binary gate. Define the conversion rule (e.g. `weight = 1 if
  priority_weight > 0 else 0`) and whether `priority_weight` survives as separate
  non-gating metadata on the concept/edge.

---

## 1. Baseline (the model we are changing)

- **Two node types only:** `tables`, `columns`. Everything else is an edge
  property or a side collection.
- **`ELEVATES` is the universal semantic predicate.** It is a self-loop on the
  column node (`_from == _to == column`) carrying `{perspective, weight, concept}`.
- **`weight` is a binary gate** (1 = in the candidate set, 0 = deactivated). It is
  not a score. weight=0 *is* suppression — there is no `SUPPRESSES`.
- **`perspective` is an edge property** (and lives on the `Perspective_*` bridge
  collections), never a node.
- **`concept` is a string** on the `ELEVATES` edge — a denormalized label. The
  real concept entity lives in SQLite (`schema_concepts`).

## 2. The change — Concept as a node (canonical target)

Concept gains identity inside the graph: a **third node type**, `concepts`. We
accept giving up the "only tables + columns are nodes" invariant in exchange for
richer traversal (column → concept → sibling columns) and a first-class home for
each concept's metadata, synonyms, and tags.

### 2.1 Node types (target)
| Node type | Source of truth | Key fields |
|---|---|---|
| `tables` | `schema_nodes` (table_type='Table') | table_name |
| `columns` | catalog / `schema_nodes` | table_name, column_name |
| `concepts` **(new)** | `schema_concepts` | concept_name, domain (family), definition, synonyms, **tags** |

### 2.2 Edge types (target)
- **`ELEVATES` becomes `column → concept`.** The concept identity moves from a
  string property onto the *target node*. The edge still carries `perspective`
  and `weight` (binary gate). A column with N meanings has N `ELEVATES` edges to
  N concept nodes (this is how `component_index` multi-meaning is expressed).
- **`has_column`** (table → column) — unchanged structural containment.
- **`references`** (child column → parent column) — unchanged structural FK.

### 2.3 Tags (settled)
Tags are a **lightweight filter only** — coarse role/type labels
(`date`, `monetary`, `quantity`, `status`, `identifier`, `polymorphic-selector`).
They carry no meaning and never gate selection. With Concept as a node, tags live
on the concept vertex (and optionally on column nodes) as a queryable array used
as an AQL prefilter before the `ELEVATES` traversal.

## 3. Source-of-truth → graph mapping (construction recipe)

| SQLite | Builds | Notes |
|---|---|---|
| `schema_concepts` | `concepts` nodes | one node per concept_name |
| `schema_concept_fields` | `ELEVATES` edges (column → concept) | carries `context_hint`, `component_index`, `is_primary_meaning` |
| `schema_perspective_concepts` | `perspective` + `weight` on the edge | `priority_weight` is normalized to the binary `weight` gate (see B3); perspective scoping |
| `schema_intent_concepts` | intent-level overrides | resolution-time, see Open Questions |

**Value-level routing (discriminator) stays in `context_hint`** for now — the
edge stays minimal; the "applies when component_type=PART" condition is carried
in SQLite, not promoted to a structured edge (see Open Questions for the fork).

## 4. Construction milestones (iterative build order)

Each milestone = one `SCHEMA_VERSION` bump + a frozen `graph_metadata.v{N}.json`,
built in **shadow collections** (B2) and accepted only when its checks pass.

1. **M1 — introduce the `concepts` node type.** Exporter emits concept nodes from
   `schema_concepts`; parser/constraints/parity learn `concept` (requires B1).
   `ELEVATES` still a self-loop string (no selection change yet).
   *Accept when:* node count rises by exactly the concept count, no edge changes,
   both parity pairs byte-identical for the new shape, HF Space app unaffected.
2. **M2 — re-point `ELEVATES` to concept nodes.** Edge `_to` becomes the concept
   node; concept identity now lives on the target, not as an edge attribute.
   **Invariant:** uniqueness/stability of multiple meanings on the same
   column+perspective is guaranteed by `_to` + deterministic `unique_id`
   allocation. The old `concept` string MAY remain during a compatibility window
   (see §7), removed in a later snapshot. Built in shadow collections; readers
   switched atomically with rollback to the prior `v{N}` (B2).
   *Accept when:* every prior self-loop has a matching column→concept edge,
   selection results are identical pre/post, parity pairs byte-identical.
3. **M3 — concept metadata + tags.** Add domain/family, definition, synonyms, and
   the curated `tags` array to concept nodes; expose them in the parity CSVs.
   *Accept when:* tags are queryable as an AQL prefilter; metadata round-trips
   through the parity CSVs; no selection change.
4. **M4 — AQL resolution + routing agent.** Ship the forward/reverse/enriched
   resolution queries; wire the private-repo routing agent to traverse
   column → concept and prefilter on tags.
   *Accept when:* the routing agent resolves a question to the same candidate set
   the SolderEngine would, against the live (shadow-then-promoted) graph.

## 5. Verification impact

The columnar parity artifacts (`graph_metadata_*.csv` from JSON,
`arango_graph_*.csv` from the live graph) and the SQL↔file / SQL↔AQL parity gates
must learn: (a) the new `concepts` node rows, (b) the re-pointed `ELEVATES`
endpoints. Their freshness-by-presence convention is unchanged. A milestone is
"done" only when both parity pairs are byte-identical for the new shape.

## 6. Reference AQL (target shape)

```aql
-- Forward: what does ONE column mean? (active, perspective-scoped)
LET col = DOCUMENT('manufacturing_graph_node/<column key>')
FOR concept, e IN 1..1 OUTBOUND col._id manufacturing_graph_edge
  FILTER e.edge_type == 'elevates' AND e.weight == 1
  RETURN { perspective: e.perspective, concept: concept.concept_name,
           domain: concept.domain, tags: concept.tags }

-- Reverse: candidate columns for an inferred perspective + concept
FOR concept IN manufacturing_graph_node
  FILTER concept.node_type == 'concept' AND concept.concept_name == @concept
  FOR col, e IN 1..1 INBOUND concept._id manufacturing_graph_edge
    FILTER e.edge_type == 'elevates' AND e.weight == 1 AND e.perspective == @perspective
    RETURN { table: col.table_name, column: col.column_name }

-- Tag prefilter (lightweight narrowing before traversal)
FOR n IN manufacturing_graph_node
  FILTER n.node_type == 'column' AND @tag IN n.tags
  FOR concept, e IN 1..1 OUTBOUND n._id manufacturing_graph_edge
    FILTER e.edge_type == 'elevates' AND e.weight == 1
    RETURN { table: n.table_name, column: n.column_name, concept: concept.concept_name }
```

## 7. Consumer compatibility & deprecation

- **Compatibility window.** During M2, the edge may carry BOTH the new `_to`
  concept identity and the legacy `concept` string so existing consumers keep
  working; the string is deprecated and removed only in a later frozen snapshot.
- **Atomic reader switch.** Consumers (HF Space app, parity gates, routing agent)
  read the promoted graph only after the shadow build passes all acceptance
  checks; a single documented step flips them, with rollback to the prior `v{N}`.
- **Deprecation ledger.** Anything removed (the self-loop edge shape, the edge
  `concept` string) is recorded here with the snapshot that removes it, so a
  consumer can see exactly when it must stop relying on the old shape.

## Open Questions

Active drift points (design-level, non-blocking for M1). Resolve → move into the
body + Decision Log. (Former Q1 "concept key format" and Q5 "live migration" were
promoted to the Pre-M1 blocking gates **B1** and **B2**.)

1. **Perspective: edge property vs. its own node/edge.** With concept as a node,
   does perspective stay an `ELEVATES` edge property, or become a
   `concept → perspective` relationship (mirroring the existing `Perspective_*`
   bridges)?
2. **Discriminator condition.** Keep value routing in `context_hint` (text, not
   traversable) or promote it to a structured `when:{column,value}` edge property
   / a graph edge sourced from `schema_edges` so the routing agent can traverse it?
3. **Intents.** How do `schema_intent_concepts` overrides surface — resolution
   time only, or as graph edges to concept nodes?

## Decision Log

| Rev | Date | Decision |
|---|---|---|
| 0.1 | 2026-06-14 | Adopt **Option C — Concept as a node** (architect strongly advocated). Tags settled as a **lightweight filter only**. Value-level discriminator routing stays in `context_hint` pending the discriminator Open Question. Drafted iterative milestones M1–M4, each a `SCHEMA_VERSION` snapshot. |
| 0.2 | 2026-06-14 | Architect review folded in: promoted concept-key grammar (**B1**) and live-graph shadow cutover/rollback (**B2**) to Pre-M1 blocking gates; added weight-normalization gate (**B3**); added per-milestone acceptance criteria, the M2 uniqueness invariant + compatibility window, and a Consumer compatibility & deprecation section (§7). |

---

*Working design notes that fed this spec: `.local/tasks/semantic-concept-tags-design.md`.*
