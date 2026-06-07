---
name: HF Space seed re-insertion & bridge drift
description: Why deleting seeded rows from the live SQLite DB alone doesn't stick, and the concept re-keying that orphans perspective_concepts.
---

# Seed re-insertion on every startup

`app.init_sqlite_db()` reads `app_schema/schema_sqlite.sql`, rewrites `INSERT INTO`
→ `INSERT OR IGNORE INTO`, and `executescript`s it on **every app startup/import**
(not just first run — the docstring says "first run" but the code runs each time).

**Consequence:** deleting a *seeded* row from the live `manufacturing.db` does NOT
stick. The next import resurrects it (with a new autoincrement id) because the seed
re-inserts any pair not currently present. There is a UNIQUE(perspective_id,
concept_id) constraint, so existing pairs are ignored but deleted ones come back.

**How to apply:** to durably remove a seeded row, edit BOTH the live DB AND the
seed file (`schema_sqlite.sql`). Editing only one is incomplete.

# Bridge drift root cause (Perspective_Concepts)

`schema_concepts` was re-keyed during curation: live ids are non-contiguous
(`1,2,3,7,8,9,26..41`), but the seed's `schema_perspective_concepts` block
hardcoded `concept_id` values `1..19`. On a *fresh* DB concepts get ids 1..19 so
all pairs are valid; on the *live* curated DB, 13 pairs (concept_ids 4,5,6,10-19)
point to concepts that no longer exist → dead-FK rows that the graph sync correctly
refuses to project (they can't become edges).

**Why the banner stayed red:** `quick_bridge_health` compares the Arango doc count
against the RAW `SELECT COUNT(*)` of the SQLite bridge table. Sync writes only the
join-valid rows, so raw(20) vs Arango(7) mismatched until the 13 dead rows were
removed from source.

# Bridge prune is ungated

`graph_sync.prune_stale_bridges` runs on EVERY sync (not behind `--purge-stale`,
unlike containment pruning) because bridge collections are pure projections of the
SQLite source — an Arango bridge row should never outlive its SQLite source row.
