---
name: Composite graph key scheme (fixed 6-slot)
description: The readable composite _key convention for the manufacturing graph and how it is parsed.
---

# Composite key scheme — FIXED 6-slot template

Every `_key` has **exactly 6 `:`-delimited slots**, parsed by **fixed position**
(no prefix tag, no slot-count branching):

```
table : column|entity : family : perspective : predicate|none : unique_id|none
  0          1            2          3              4               5
```

- table node      `PAYABLE:entity:structural:system:none:none`
- column node     `PAYABLE:INVOICE_ID:structural:system:none:none`
- structural edge `PAYABLE:INVOICE_ID:structural:system:has_column:<UID>`
- semantic edge   `PAYABLE_LINE:RECEIVER_ID:semantic:Payables:elevates:<UID>` (DEFERRED v2)

**Classify:** it is a NODE iff `slot[4]=='none' and slot[5]=='none'` (table node
if `slot[1]=='entity'`, else column node); otherwise it is an EDGE whose family
is `slot[2]` (`structural` | `semantic`).

**Why:** the user moved from a variable-width scheme to a fixed 6-slot template
so parse position is constant and node-vs-edge is a trivial `none:none` check.
This finally makes edge keys impossible to confuse with node keys (the old
4-slot column-vertex vs structural-edge collision is gone).

**How to apply:**
- Reserved tokens — the exporter HARD-FAILS if a source name collides:
  `entity` (no column may be named it), `none` (no column/table may be named it),
  `system` (no business view may be named it; it marks the structural layer).
- Components must be non-empty and contain no `:` or `/`.
- Edges fill slots 4-5 with predicate + unique_id; the structural containment
  predicate is `has_column`.
- **UNIFIED abbreviated uid grammar — BOTH layers share ONE slot-5 form** (the
  earlier "structural = full-name, semantic = abbreviated" split was REVERSED by
  the architect): `perspective(3)_edge_type(3)_table(3)_column|entity(3)_uniqifier(3)`.
  - structural example: `SYS_HAS_PAY_INV_001` on key
    `PAYABLE:INVOICE_ID:structural:system:has_column:SYS_HAS_PAY_INV_001`
  - semantic example: `PAY_ELE_PAY_INV_001` on key
    `PAYABLE:INVOICE_ID:semantic:Payables:elevates:PAY_ELE_PAY_INV_001` (DEFERRED)
  - Abbrev = first 3 alphanumeric chars uppercased. Collisions are EXPECTED
    (INVOICE_ID/INVENTORY → INV; cert_id/cert_type → CER) and resolved by the
    uniqifier, so the uid is ALLOCATED (counted), not purely derived.
  - **This means the STRUCTURAL export now also needs allocation, not just a pure
    function.** `allocate_containment_uids()` sorts columns by (table,column) and
    counts up from 001 per `SYS_HAS_<T3>_<C3>` prefix — deterministic per fixed
    DB (re-run = identical uids), but adding a column that sorts before an
    existing collision-mate WILL re-number the later one (inherent to allocated
    uids; acceptable, it's a from-scratch regenerated snapshot).
  - Uniqifier scope = per `(perspective, edge_type, table, column|entity)` prefix,
    default `001`. **One edge_type *key* per perspective** — the 3-char edge_type
    abbreviation is namespaced inside its perspective (not one global edge_type).
  - v2 open question is only the semantic-edge data source + `_to` target
    (self-loop vs concept node).
- **No one-table-one-perspective assumption.** A single physical table can host
  multiple logical entities split by a discriminator column (e.g. an
  engineering-master / work-order table holding an engineering entity AND a
  manufacturing entity in different perspectives). This is why slot 1 is
  `column|entity` — keep entity granularity open; do NOT add a guard binding a
  table to a single perspective.
- **`replit_integrations/graph_metadata.json` is the CANONICAL TARGET (the plan),
  NOT a mirror of the live graph.** It embeds the full grammar in a `key_scheme`
  block, is stamped `metadata_version`/`milestone_name`, uses collections
  `manufacturing_graph_node` / `manufacturing_graph_edge`, and the exporter
  freezes a create-once snapshot `graph_metadata.v{metadata_version}.json`. The
  LIVE ArangoDB still uses old `column::TABLE.COLUMN` keys (`arangodb_helpers`,
  `migrations`, `scripts`) — untouched; the export does not run in CI.
- Current milestone `database_bound_unambiguous_slots` = structural footprint
  only (table+column nodes + has_column edges).
- Reference artifacts: `graph_metadata.canonical_example.json` (hand-verified,
  4 records) and assertions in `graph_metadata_demo.py` (Example 4).
