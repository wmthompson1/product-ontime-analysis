# Canonical Graph Construction — Concept as a Node

> **Status:** LIVING — M2 complete (M3+ pending)
> **Revision:** 0.6
> **Last updated:** 2026-06-14
> **Baseline graph:** `graph_metadata.v14.json` (`SCHEMA_VERSION = 14`, concept nodes + re-pointed `elevates`)
> **Current milestone:** M2 — `elevates` re-pointed to concept nodes (COMPLETE); M3 (richer concept payload) next

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

Per architect review (Rev 0.2), these are **gates**, not open musings, each
resolved and recorded in the Decision Log before the milestone it guards. **B1**
gates M1 (the identity-only concept-node addition) and is now **resolved** (Rev
0.3). **B2** (shadow cutover/rollback) and **B3** (weight normalization) gate the
edge-changing milestones (M2+): M1 only adds inert concept-node rows and touches
no edge, so it does not trip them.

- **B1 — Concept `_key` grammar. — RESOLVED (Rev 0.3).** Ratified grammar:
  `<ConceptName>:entity:semantic:canonical:none:none` — slot 0 = concept name,
  slot 1 = `entity` placeholder (a concept, like a table, has no column), slot 2 =
  `semantic` family (a concept is a meaning-layer node, **not** structural), slot 3
  = `canonical` (a concept is perspective-agnostic — a perspective attaches later
  on the `elevates` edge, not on the concept), slots 4–5 = `none`. **Classifier
  (node-first, then family):** a key is a NODE iff `slot[4:6]==['none','none']`; a
  node is a *concept* iff `slot[2]=='semantic'`, else a *table* iff
  `slot[1]=='entity'`, else a *column* (tables and columns are both `structural`).
  This is unambiguous because a semantic *edge* (`elevates`) always carries a
  predicate **and** a business perspective, so `semantic` + node can only be a
  concept. The `node_type` enum (`table`/`column`/`concept`), reserved tokens (a
  concept name may not equal any grammar token — `entity`, `none`, `system`,
  `canonical`, `structural`, `semantic`; a business perspective may not be `system`
  or `canonical`), the SQL CHECK constraints, and both parity flatteners now admit
  `concept`. **Two reserved perspective scopes:** `system` is the structural-layer
  scope (tables, columns, FK edges); `canonical` is the perspective-agnostic scope
  owned by concept nodes.
- **B2 — Shadow-graph cutover + rollback. — RESOLVED (Rev 0.5).** Re-pointing
  `ELEVATES` in place would break any consumer expecting self-loop edges with a
  `concept` string — but there is **no such live consumer**: the HF Space app reads
  the legacy named graph (`ELEVATES`/`HAS_COLUMN`/… collections), never the
  canonical `manufacturing_graph_node`/`manufacturing_graph_edge` collections this
  exporter owns. A literal shadow graph is therefore unnecessary. **Resolution:**
  the safety a shadow would give is provided by (1) the freeze-once
  `graph_metadata.v{N}.json` snapshot per milestone, (2) both parity gates
  (SQL↔file byte-identical, SQL↔live-AQL field-for-field) gating every change, and
  (3) a documented rollback to the prior frozen snapshot. The live load
  (`load_canonical_to_arango.py`) is **truncate-then-import on the canonical
  node/edge collections only** (idempotent, keyed on `_key`), so it never touches
  the legacy graph the app reads. **Rollback path:** re-import the prior
  `graph_metadata.v13.json` into the canonical collections (same loader, same
  truncate-then-import) and revert `SCHEMA_VERSION`.
- **B3 — Weight normalization. — RESOLVED (Rev 0.5).**
  `schema_perspective_concepts.priority_weight` is not the binary gate. **Rule:**
  `weight = 1 if (priority_weight or 0) > 0 else 0` — `weight` stays the binary
  candidate-set gate (1 = selectable, 0 = suppressed). **`priority_weight`
  survives** as a separate non-gating metadata field on the `elevates` edge (new
  `sql_graph_edges.priority_weight` column), so the SME's raw priority is preserved
  for later ranking without overloading the gate.

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

1. **M1 — introduce the `concepts` node type. — COMPLETE (v13).** Exporter emits
   concept nodes from `schema_concepts`; parser/constraints/parity learn `concept`
   (B1 resolved). **M1 payload is identity-only: `concept_name` + `description`**
   (the `<ConceptName>:entity:semantic:canonical:none:none` key plus a human
   description); richer metadata (type, domain, synonyms, tags) is deferred to M3.
   `ELEVATES` still a self-loop string (no selection change yet).
   *Accept when:* node count rises by exactly the concept count, no edge changes,
   both parity pairs byte-identical for the new shape, HF Space app unaffected.
2. **M2 — re-point `ELEVATES` to concept nodes. — COMPLETE (v14).** Edge `_to`
   becomes the concept node (`_from` stays the column); concept identity now lives
   on the target, not as an edge attribute. Node/edge counts are unchanged (the 17
   self-loops become 17 column→concept edges); only the endpoints move.
   **Concept string dropped now (no compatibility window — user decision):** the
   concept node is the single home for concept identity, so the `concept` field is
   removed from the JSON edge **and** the `sql_graph_edges.concept` column in this
   same snapshot (see §7 deprecation ledger). The concept name remains an *input*
   to the uid, just not a stored edge property.
   **Uniqueness/stability invariant:** the `elevates` `unique_id` is no longer a
   per-prefix counter — it is **concept-aware and deterministic**, derived from the
   natural key `(perspective, table, column, concept, field_component)` via
   `semantic_uid_stable(...)`. Adding or removing a sibling concept on the same
   column+perspective therefore does **not** renumber unrelated edges. The 6-slot
   key grammar is unchanged (no 7th slot); the key still encodes the *source*
   column and the concept lives only on `_to`. Two concepts on the same
   column+perspective get distinct uids (distinct hash) → distinct keys.
   **Both endpoints guarded:** an elevation whose column is not an exported node OR
   whose concept has no concept node is skipped and recorded in
   `integrity["semantic_elevations_skipped"]`.
   **B2 cutover:** built as a freeze-once `v14` snapshot, accepted only when both
   parity pairs pass, then loaded into the canonical collections
   (truncate-then-import, legacy graph untouched), with rollback to `v13`.
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

- **Compatibility window — waived for M2 (user decision).** The plan allowed the
  edge to carry BOTH the new `_to` and the legacy `concept` string for a window. We
  **skipped the window**: there is no live consumer of the canonical edges (the HF
  Space app reads the legacy named graph), so the `concept` string is removed in the
  same `v14` snapshot that re-points the edge. The concept node is the single home
  for concept identity.
- **Atomic reader switch.** Consumers (parity gates, future routing agent) read the
  promoted graph only after the build passes both parity gates; the live load is a
  single truncate-then-import step, with rollback to the prior `v{N}`.
- **Deprecation ledger.** What was removed, and the snapshot that removed it:

  | Removed | Snapshot | Replacement |
  |---|---|---|
  | `ELEVATES` self-loop shape (`_from == _to == column`) | v14 | `column → concept` edge (`_to` = concept node) |
  | `concept` string on the `elevates` edge | v14 | the `_to` concept node (identity lives on the target) |
  | `sql_graph_edges.concept` column | v14 | `_to` + new `sql_graph_edges.priority_weight` (raw SME priority) |

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
| 0.3 | 2026-06-14 | **B1 resolved.** Ratified the concept `_key` grammar `<ConceptName>:entity:semantic:canonical:none:none` (a concept is a **semantic-family** node, not a new family; perspective-agnostic concepts get the dedicated **`canonical`** perspective so `system` stays the structural-layer scope) with a **node-first classifier** (node iff slots 4–5 are `none`; concept if slot 2 is `semantic`, else table if slot 1 is `entity`, else column). Scoped **M1 to a minimal identity-only payload** (name + description); type/domain/tags deferred to M3. B2/B3 reaffirmed as gates for the edge-changing milestones (M2+), not M1. Froze `SCHEMA_VERSION = 13` (`concept_nodes_introduced`). |
| 0.4 | 2026-06-14 | **M1 complete.** Exporter emits the concept nodes; node count rose by exactly the concept count with no edge changes; both parity pairs (SQL↔file, SQL↔live-AQL) byte-identical for the new shape; the canonical was loaded into the live ArangoDB (additive nodes only — does not trip B2); HF Space app unaffected (resolvers filter `node_type` to table/column). Hardened the SQLite upgrade path so an old `sql_graph_nodes` that has had only `concept_name` bolted on by the app boot guard is still rebuilt (the old `node_type` CHECK + `table_name NOT NULL` are detected, not just the missing column). |
| 0.5 | 2026-06-14 | **B2 + B3 resolved; M2 in progress (v14).** B2: no live consumer reads the canonical edges (the HF app uses the legacy named graph), so the shadow graph is waived — safety comes from the freeze-once `v{N}` snapshot, both parity gates, and a documented rollback to `v13`; the live load is truncate-then-import on the canonical collections only. B3: `weight = 1 if (priority_weight or 0) > 0 else 0`, with `priority_weight` kept as non-gating edge metadata (new `sql_graph_edges.priority_weight`). M2: re-pointed `ELEVATES` to `column → concept`; **dropped the `concept` string now (no compatibility window — user decision)** from both the JSON edge and the `sql_graph_edges.concept` column; made the elevates uid concept-aware/deterministic via `semantic_uid_stable(perspective,table,column,concept,field_component)` so sibling churn no longer renumbers edges; guarded both endpoints. Froze `SCHEMA_VERSION = 14` (`elevates_repointed_to_concepts`); counts unchanged 279/279 (17 elevates re-pointed). |
| 0.6 | 2026-06-14 | **M2 complete (v14).** Loaded the re-pointed canonical into live ArangoDB — 279 nodes / 279 edges, all endpoints resolve, 17 `elevates` now `column → concept`; both parity pairs byte-identical (SQL↔file, SQL↔live-AQL). Realigned the two remaining format-lock suites to the M2 shape: `test_semantic_scaffolding.py` (column→concept, no `concept` string on the edge, binary `weight` derived from `priority_weight`, concept-aware/stable uid, both-endpoint guard) and `test_authored_edges_merge.py` (authored SME weight folds into the elevation feed as `priority_weight` + `field_component`). `bash scripts/post-merge.sh` EXIT=0; both apps boot unaffected (HF Space :8080 Gradio serving, Flask :5000). |

---

*Working design notes that fed this spec: `.local/tasks/semantic-concept-tags-design.md`.*
