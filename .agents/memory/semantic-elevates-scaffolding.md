---
name: Semantic elevates scaffolding
description: How the canonical exporter wires the semantic elevates layer so plumbing is live but content stays empty until SME curation.
---

The exporter builds semantic `elevates` edges from SQLite (the source of truth)
but they stay at **zero content** by design — "scaffolding now, content later".

**Source join (SQLite):** `schema_concept_fields` (table,field→concept) ⋈
`schema_perspective_concepts` (concept→perspective + priority_weight) ⋈
`schema_perspectives` (id→name) ⋈ `schema_concepts` (id→name).

**Edge shape (locked, matches `graph_metadata_canonical_example.json`):** a
self-loop on the column node — `_from == _to == column_id` — family `semantic`,
type `elevates`, carrying `perspective`, `weight`, `concept`. Key is the 6-slot
`table:column:semantic:{perspective}:elevates:{uid}`; uid via the same
abbreviated allocator as references (`PAY_ELE_PAY_INV_001`).

**Why zero edges emit today:** the only curated `schema_concept_fields` rows
target `stg_manufacturing_flat`, a staging table that is NOT one of the 22
canonical business nodes. The builder guards endpoints exactly like references
edges — a column not in the exported node set is skipped and recorded in
`integrity["semantic_elevations_skipped"]`, never emitted as a dangling edge. It
lights up automatically when an SME maps a real ERP column.

**Invariants enforced:** perspective may never be the reserved token `system`
(owned by the structural layer) — `semantic_edge_key` hard-fails on it. The
loader cross-checks the dual invariant: structural edges are always `system`,
semantic edges never are.

**How to apply:** to add real elevations, insert `schema_concept_fields` rows
pointing at canonical business `table.column` pairs (lowercase, matching node
keys) + link the concept to a perspective in `schema_perspective_concepts`, then
re-run the exporter and loader. No code change needed.
