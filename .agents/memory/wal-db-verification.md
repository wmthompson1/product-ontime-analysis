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
