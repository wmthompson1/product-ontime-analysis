---
name: Canonical graph can lag seed_elevations.py
description: Why a graph re-export for an unrelated change can surface extra resolves_to edges you didn't add
---

The committed canonical `graph_metadata.json` (and its `sql_graph_*` tables) is a
frozen snapshot from the last `export_graph_metadata.py` run. The resolves_to /
elevation bindings it contains are DERIVED at export time from the live SQLite
`schema_concept_fields`, which is itself seeded by `replit_integrations/seed_elevations.py`.

**Rule:** `seed_elevations.py` (a committed seed, run by `post-merge.sh`) can be
updated with new column→concept bindings WITHOUT anyone re-exporting the canonical
graph. When that happens the committed graph is stale — it has fewer resolves_to
edges than the seed would produce. The next re-export for ANY unrelated reason
picks up those already-defined-but-never-exported bindings.

**Why this matters:** if you re-export the graph for a small change (e.g. adding one
column) and the `resolves_to` count jumps by more than your change explains, do NOT
assume you caused it. Grep `seed_elevations.py` for the concept names on the new
edges — if the bindings are defined there, they are legitimate and reproducible, and
your re-export simply corrected pre-existing staleness.

**How to apply:** confirm reproducibility against `seed_elevations.py` (not your
migration) before treating a resolves_to delta as your bug. The DB is gitignored and
rebuilt from seed, so "reproducible from the committed seed scripts" is the only test
of whether an exported edge belongs.
