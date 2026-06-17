---
name: WAL-mode DB migration verification
description: How to verify/idempotency-check SQLite migrations in this repo's WAL-mode app DB, and where that DB actually lives.
---

# Verifying SQLite migrations in the WAL-mode manufacturing DB

The app DB (`hf-space-inventory-sqlgen/app_schema/manufacturing.db`) runs in WAL
mode and is **gitignored** — the durable, version-controlled artifact is the
migration script, not the DB. Migrations evolve the persistent workspace DB in
place (same pattern as `add_operation_type.py`); nothing in post-merge or app boot
rebuilds it. So `replit.md`'s "committed shipping DB" wording is loose: it persists
in the workspace, but git does not track it.

**WAL gotcha (cost an extra verification round):** copying just the main `.db`
file (`cp` / file-level md5) misses committed-but-uncheckpointed rows that still
live in the `-wal` file (and `-wal`/`-shm` are gitignored too). The tell is an
empty-string md5 (`d41d8cd98f00b204e9800998ecf8427e`) for a table you know is
non-empty.

**How to apply:**
- To diff or idempotency-check a migration, query through `sqlite3` (it reads
  main+WAL together), never by copying the file.
- Prove a migration is a fixed point: dump tables via sqlite3 → run migration →
  dump again → diff; they should be byte-identical.
- Before trusting the main file standalone (or finishing a DB task), checkpoint:
  `PRAGMA wal_checkpoint(TRUNCATE);` then `PRAGMA integrity_check;`. Do it when no
  workflow holds the DB open (stop the HF Space workflow first if needed).

## Dropping a column hides breakage until a FRESH DB is built

**Why:** the gitignored WAL dev DB persists in place and is never rebuilt by boot
or post-merge, so when you remove a column from `schema_sqlite.sql` the dev DB
**still physically has the old column** — every `SELECT col …` keeps working
locally and the whole gate can pass green. The break only surfaces on a *fresh*
DB created from the (now-purged) schema, e.g. a CI clone or a deleted-then-
recreated DB. This is the inverse of the original "stale DB missing a new column"
500, and it cost two extra discovery rounds (alternate sync utility + a read-only
query-template library were both missed by a casual scan).

**How to apply:** when removing/renaming a physical column, do NOT trust the live
DB. (1) `rg` the WHOLE repo for every read/write of that column name — include
query-template libraries, alternate `refresh_*`/sync scripts, and demos, not just
the obvious app readers; (2) validate by building a throwaway DB straight from
`schema_sqlite.sql` and executing each touched query against it (empty tables are
enough to catch `no such column`); (3) prefer a derived alias that preserves the
old output column shape so callers/tuple-indices are untouched.
