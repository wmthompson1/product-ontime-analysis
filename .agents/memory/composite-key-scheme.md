---
name: Composite graph key scheme (slot-length parsing)
description: The readable composite _key convention for the manufacturing graph and how it is parsed.
---

# Composite key scheme

Keys are readable, `:`-delimited, **broad-first**. Parsing is by **slot count +
terminal/family tokens alone** — no prefix tag:

- `table:family:perspective` — 3 slots → **table vertex** (e.g. `EMPLOYEE:structural:system`)
- `table:column:family:perspective` — 4 slots, perspective `== 'system'` → **column vertex**
- `table:column:family:perspective` — 4 slots, perspective is a business view (e.g. `payable`) → **core structural edge**
- `table:column:family:perspective:predicate:UniqueID` — 6 slots, family `== 'semantic'` → **semantic edge** (e.g. `PAYABLE:INVOICE_ID:semantic:payable:elevates:PAY_ELE_PAY_INV_001`)

For 3/4-slot structural keys the perspective is the terminal slot; for 6-slot
semantic keys, family (slot 2) is the discriminator and predicate+UniqueID follow.

**Why:** the user chose per-type slot subsets (not a fixed template) and wanted
keys unambiguous to parse/search without a type tag. Slot count + the reserved
`system` perspective + the `semantic` family make classification deterministic.

**How to apply:**
- `family='structural'`, `perspective='system'` for the structural layer
  (family and perspective intentionally DIFFER).
- `'system'` is reserved — a business view may never be named `system`.
- Components must not contain `:` (the delimiter) or `/` (ArangoDB key ban).
- **`intent` and `UniqueID` are DEFERRED** — not bound to the physical schema
  footprint; do not add them to structural keys for now.
- Reference implementation + assertions live in
  `replit_integrations/graph_metadata_demo.py` (Example 4).
- **`replit_integrations/graph_metadata.json` is the CANONICAL TARGET (the plan),
  NOT a mirror of the live graph.** It now uses composite keys and embeds the
  full grammar in a `key_scheme` block + `schema_version`/`milestone` stamp; the
  exporter freezes a create-once snapshot `graph_metadata.v{N}.json`. The LIVE
  ArangoDB still uses the old `column::TABLE.COLUMN` keys (see `arangodb_helpers`,
  `migrations`, `scripts`) — those are untouched and the export does not run in CI.
- **v1 milestone = structural footprint only** (table/column vertices + CONTAINS).
  Perspective-scoped structural edges + 6-slot semantic edges are DEFERRED to v2,
  and v2's open question is the data source for semantic `elevates` edges.
