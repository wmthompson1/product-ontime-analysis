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
  predicate is `has_column`. Auto-generated containment unique_id is the
  full-name form `{table}_{column}_CONTAINMENT` (abbreviations can't be derived
  deterministically; swap `contains_edge_unique_id` to change the convention).
- The **semantic layer (6-slot, family `semantic`) is DEFERRED** — format locked
  but not populated; v2 open question is the semantic-edge data source AND the
  semantic unique_id convention (user is taking that to the architect agent).
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
