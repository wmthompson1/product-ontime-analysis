---
name: Fresh-DB graph restore path
description: Why a fresh-bootstrap manufacturing.db cannot regenerate the frozen sql_graph tables and how the restore path works
---

# Fresh-DB graph restore

**Rule:** A fresh-bootstrap `manufacturing.db` can NEVER re-derive the frozen graph: the exporter's bridge feeds (`schema_topology_metadata`, curated elevations, authored edges) are not part of the bootstrap chain. The committed `graph_metadata.json` is the only surviving copy on main (the DB is gitignored). Restore direction inverts: JSON → `sql_graph_*` tables via `replit_integrations/import_graph_metadata.py` (refuses to overwrite populated tables; post-merge takes this branch only when `sql_graph_nodes` is empty).

**Why:** After a task merge rebuilt main's DB fresh, the old self-heal path (seed_elevations → export) hard-failed and could not reproduce the 366-node/423-edge frozen graph anyway.

**Two hidden ordering dependencies on fresh DBs:**
1. `seed_elevations.py` references perspectives (e.g. Finance) absent from the 13-perspective `schema_sqlite.sql` seed — it now self-seeds them (NEW_PERSPECTIVES manifest, INSERT OR IGNORE by name).
2. The schema seed's intent→concept link inserts are name-based `INSERT..SELECT`s that silently insert ZERO rows when concepts don't exist yet (concepts come from seed_elevations, which runs later). Fix: re-apply the schema seed AFTER seed_elevations with the boot-style `INSERT INTO`→`INSERT OR IGNORE INTO` transform. Raw executescript of the seed WITHOUT that transform fails on `operation_type` UNIQUE.

**How to apply:** if the parity gate fails and `sql_graph_nodes` is empty → seed_elevations, re-apply schema seed (OR IGNORE transform), import_graph_metadata.py. Never run the import on a populated-but-stale DB — use the seed+export re-materialization path instead.

**Structural FKs on fresh DBs:** fresh DDL also lacks the declared FKs the frozen graph records — `migrations/declare_structural_fks.py` (last bootstrap step) re-declares them from the JSON's `references` edges via writable_schema. Declare BOTH origins (`fk_declared` AND `sql_observed`) — the metric join resolver needs sql_observed-only links (e.g. purchase_order→receiving) — but dedupe tuples first: the JSON carries origin twins for a few pairs, and naive per-edge appends emit duplicate FOREIGN KEY clauses in DDL.
