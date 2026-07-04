# Plan: Graph-aware structural fingerprint (base tables → base tables + join edges)

## Objective
Make the graph an **active join validator** without ever generating SQL. Extend the
structural fingerprint from "the set of base tables a snippet touches" to also cover
"the set of join edges a snippet uses", and fail closed when a snippet joins two
tables via a relationship the graph does not recognize. Feed the extractor's
discovered join lineage back into the graph so the recognition check is correct
(not over-rejecting).

## Invariant guardrail
SME-approved SQL stays the sole source of joins. The graph never supplies or infers
a join — it only **recognizes / rejects** the joins already written in approved SQL.

---

## 1. Join-edge canonical form (the unit being fingerprinted)
Each equi-join in a snippet reduces to a **column-qualified, alias-free,
type-bearing** tuple:

    JoinEdge = (table_a, column_a, table_b, column_b, join_type)

Derivation from the extractor's `JoinRelationship`:
- Resolve `left_key`/`right_key` back to their owning **table** using the alias→table
  map built from the FROM/JOIN clause (aliases are query-local, the graph knows tables).
- Canonical order: sort the two `(table, column)` endpoints lexicographically for a
  stable key, AND express `join_type` **relative to that order** — when the sort swaps
  the sides, flip `LEFT`↔`RIGHT` (INNER/FULL/CROSS are symmetric, unaffected). This
  yields one canonical edge per relationship while preserving optionality semantics.
- Lowercase table + column names (matches base-table casing rule).

Design decisions (per user, revised):
- **Column-qualified, not table-pair** — fixes the "lossy dedup" concern; two
  different relationships between the same table pair are distinct edges.
- **Join TYPE IS part of the validated key** — a LEFT vs INNER join is ontological
  meaning (optional vs mandatory participation), not cosmetic style. So an SME's
  INNER→LEFT rewrite DOES change the fingerprint and requires re-approval. (DECIDED)
- **Equi-joins only for validation** — only `exp.EQ` column=column predicates yield a
  validated JoinEdge. Non-equi / CROSS / alias-unresolvable joins go into
  `unresolved_joins` (warn, never block — see §4).

## 2. Expanded fingerprint stored on the manifest entry
```jsonc
"structural_fingerprint": {
  "base_tables": ["customer_order_line", "part"],            // unchanged
  "join_edges": [                                            // NEW (sorted, deduped)
    {"table_a":"customer_order_line","column_a":"part_id",
     "table_b":"part","column_b":"part_id","join_type":"INNER"}
  ],
  "unresolved_joins": [                                      // NEW: cross/non-equi/unresolved
    // {"reason":"cross_join","tables":["a","b"]}
  ],
  "extractor_id": "sqlglot-sqlite-base-tables+join-edges-v2" // bumped v1 -> v2
}
```
`extractor_id` is bumped v1→v2 for EVERY entry in the same migration — **no grace
period, hard cutover** (§6). There is no v1/v2 coexistence at runtime: after the
migration every entry carries a join dimension and the join gate enforces for all.

## 3. Graph adjacency the fingerprint validates against
Build a cached set `graph_join_edges` in the SAME canonical form, from the graph's
`references` edges: each edge gives child (`_from` node → table:col) and parent
(`references_table` / `references_column`).

**Coupling (why write-back is required, not optional):** today the graph has only 39
FK-derived edges, but approved snippets join on more than declared FKs. So the
extractor's discovered `join_edges` are upserted back into the graph (idempotent
UPSERT, mirroring existing duplicate-edge protection) as **first-class STRUCTURAL
edges** — same `edge_family = structural` layer as `references`, part of ONE ontology
mosaic (NOT a segregated `join_lineage` provenance silo). Provenance is kept as an
edge **property** (`origin`: `fk_declared` | `sql_observed`) plus `join_type`, so we
never falsely assert referential integrity we don't have, while still unifying joins
and FKs into one structural graph. `graph_join_edges` = every structural relationship
edge (FK references + observed joins) in the canonical §1 form. Without write-back a
correct snippet joining on a non-FK column would wrongly fail closed.

## 4. New validation function (additive, alongside validate_fingerprint)
    validate_join_edges(sql_text, approved_join_edges, graph_join_edges) -> (ok, reason, warnings)

Two blocking checks (equi-joins only):
- (a) **Drift**: snippet's current equi-join-edge set (incl. `join_type`) must equal
  the manifest's approved `join_edges` — adding/removing a join, or changing its type,
  is a structural change needing re-approval.
- (b) **Recognition**: every snippet equi-join edge must exist in `graph_join_edges`;
  unrecognized → fail closed. This is the "graph as active validator" chosen.

Non-blocking:
- `unresolved_joins` (CROSS / non-equi / alias-unresolvable) → **warn, never block**.
  These are legitimate in approved SQL (e.g. time-phasing range joins). The base-table
  fingerprint still bounds which tables they can reach, so the invariant holds; the
  warning surfaces them for SME visibility.

## 5. Wiring into assemble_query / dispatch (extends fail-closed condition 4)
Condition 4 today = base-table mismatch. Extend it to also fire on join-edge drift or
unrecognized join, reusing the fail-closed hard-refusal path hardened this session.
New `fail_closed_condition` values: `join_fingerprint_drift`, `join_not_in_graph`.
Enforced for ALL entries immediately (hard cutover — no v1 skip). `unresolved_joins`
attach as warnings on the served result, not as fail-closed conditions.

## 6. Backfill / migration (hard cutover, ends fail-closed)
- Re-fingerprint EVERY manifest entry in one pass: parse → extract canonical join
  edges (with `join_type`) → write `join_edges` + `unresolved_joins`, bump
  `extractor_id` to v2.
- Graph write-back: union of all discovered equi-join edges → idempotent UPSERT as
  structural edges (`origin=sql_observed`) into the references/structural layer;
  re-export bumps SCHEMA_VERSION; parity + coverage gates re-run in post-merge.
- **Migration ends with a fail-closed validation** (same pattern as
  `validate_planning_inputs`): assert every approved snippet's equi-join edges are now
  recognized in `graph_join_edges`. If any are not, the migration ABORTS loudly rather
  than shipping a gate that would refuse on boot. This is what makes an immediate
  hard cutover safe.
- New tests: canonical-form normalization (incl. LEFT↔RIGHT flip on endpoint swap),
  drift (incl. type change), recognition, unresolved-join warn-not-block, alias→table
  resolution, one-canonical-edge-per-relationship, migration completeness assertion.

## Decisions locked (from user review)
1. Join TYPE **is** part of the validated key (optionality is ontology).
2. Discovered joins fold into the **structural** layer (one mosaic), provenance as a
   property — not a distinct `join_lineage` edge type.
3. **No grace period** — hard cutover; every entry re-fingerprinted + enforced at once.
4. Non-equi/CROSS joins **warn, never block**.

5. Directionality: canonicalize by sorting endpoints lexicographically and flipping
   `LEFT`↔`RIGHT` when the sort swaps sides (INNER/FULL/CROSS symmetric) — one
   canonical edge per relationship, with join type + order specified on it.

## Status
Schema fully specified and locked. No open questions. Ready to be turned into a
build task on request (not auto-created, per user preference).
