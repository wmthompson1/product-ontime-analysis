---
name: Ground-truth views, not snippets
description: User terminology correction — the archived POC grounding SQL files are full views/datasets that function as metadata, not snippets.
---

# Ground-truth "views" — the term "snippets" is misleading for the grounding queries

The rule: the POC-era grounding queries archived under
`ground_truth/sql_snippets/_archived/` (capacity planning, customer-order
demand, shop-floor routing, inventory transactions T-SQL + SQLite pair) are
NOT snippets. Each is a complete, self-contained **view / dataset
definition** — run whole or not at all. Their real value is as **metadata**:
they declare which tables ground a business question, the canonical joins,
and the derivation rules (signed qty effects, load = setup + run hours,
reconciliation flags). Same semantic family as `graph_metadata.json` and the
bridge tables, expressed as SQL.

**Why:** User stated this explicitly (2026-07-04): "Snippets is misleading,
they are full views aka datasets but importantly they are metadata." True
snippets are the fragment-level SME-approved pieces SolderEngine assembles
via structural fingerprints — a different thing.

**How to apply:** In prose, docs, and new code, call these grounding files
"governed views" / "datasets" / "grounding queries," never snippets. The
`sql_snippets/` directory name is legacy — do not rename it casually (paths
ripple through code, docs, and the Ontop POC), but if a rename is ever
requested the target vocabulary is views/datasets.
