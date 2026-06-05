---
name: Composite graph key scheme (slot-length parsing)
description: The readable composite _key convention for the manufacturing graph and how it is parsed.
---

# Composite key scheme

Keys are readable, `:`-delimited, **broad-first**, with the **perspective always
the terminal slot**. Parsing is by **slot count + terminal token alone** — no
prefix tag:

- `table:family:perspective` — 3 slots → **table vertex**
- `table:column:family:perspective` — 4 slots, perspective `== 'system'` → **column vertex**
- `table:column:family:perspective` — 4 slots, perspective is a business view (e.g. `payable`) → **core structural edge**

**Why:** the user chose per-type slot subsets (not a fixed template) and wanted
keys unambiguous to parse/search without a type tag. Slot count + the reserved
`system` perspective makes classification deterministic.

**How to apply:**
- `family='structural'`, `perspective='system'` for the structural layer
  (family and perspective intentionally DIFFER).
- `'system'` is reserved — a business view may never be named `system`.
- Components must not contain `:` (the delimiter) or `/` (ArangoDB key ban).
- **`intent` and `UniqueID` are DEFERRED** — not bound to the physical schema
  footprint; do not add them to structural keys for now.
- Reference implementation + assertions live in
  `replit_integrations/graph_metadata_demo.py` (Example 4).
