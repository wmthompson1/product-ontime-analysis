---
name: HF Space test suite has slow Arango network tests
description: Why full pytest of hf-space-inventory-sqlgen/tests exceeds the 120s bash budget and how to run it
---

Several test files in `hf-space-inventory-sqlgen/tests/` (bridge-health-after-sync, commit-edge*, delete-commit-edge, db-init-self-heal) make live ArangoDB network calls and take ~15s each, so a full `pytest tests/` run blows past the 120s bash-tool cap and looks hung.

**Why:** remote Arango round-trips, not broken tests — they pass given time.

**How to apply:** run the suite in file batches (first/second half) or per-file with generous timeouts; never conclude "hang" from a silent 12s-per-file probe. Also: Arango count-parity tests can fail transiently right after registry changes and self-heal once the app restarts and sync_watcher pushes rows — re-check before treating as a regression. Backgrounded (`nohup`/subshell `&`) pytest gets killed when the bash tool session exits, so don't rely on detached runs.
