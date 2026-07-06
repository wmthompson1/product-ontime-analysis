---
name: Selector query registration
description: What it takes for a new palette query to appear in the Selector v1.0 ground-truth query dropdown
---

# Selector query registration

A `-- Query:` entry in a palette file is NOT enough to appear in the Selector
v1.0 "Ground-truth query" dropdowns. The dropdown is built from SQLite
`schema_intent_queries` (reachable via `schema_intent_concepts` weight-1 →
intent → query), so every new palette query needs an intent→query row.

**Why:** the selector chain is DB-driven (concept/intent bridges), while the
palette tab parses the files directly — a query can work in one and be
invisible in the other.

**How to apply:**
- Add an `INSERT OR IGNORE` row into `schema_intent_queries` (via a migration
  registered in the bootstrap chain) under the right intent.
- `query_index` is the 0-based position of the `-- Query:` marker in the file.
  Inserting a query mid-file SHIFTS later queries' indices; the unique index
  `(intent_id, query_file, query_index)` means you must UPDATE displaced rows
  to their new index BEFORE inserting the new row at the vacated slot.
- `query_index` is ordering/metadata only — SQL resolves by `query_name` — but
  keep it matching file order anyway.
- Verify end-to-end via `/gradio/config` (dropdown choices should list the
  new query name in all Selector dropdowns).
