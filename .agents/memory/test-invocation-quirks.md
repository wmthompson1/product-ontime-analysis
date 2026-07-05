---
name: Test suite invocation quirks
description: How to run this repo's tests the authoritative way and which failures are invocation artifacts, not regressions.
---

**Rule:** Validate tests the gate's way — `python tests/<file>.py` per file (as `scripts/post-merge.sh` does), never big pytest batches.

**Why:** pytest batching multiple test files shares process/DB state and produces false failures (e.g. delete-commit-edge 404 tests fail in a batch but pass 5/5 standalone). The gate runs 50+ files individually.

**How to apply:**
- Full suite exceeds the 120s bash limit — loop files in chunks of ~5-8 with per-file `timeout 60`, logging to /tmp.
- `tests/test_schema_tab.py` (repo root, not in gate) needs `PYTHONPATH=hf-space-inventory-sqlgen` to import `solder_engine`.
- `test_bridge_health_after_sync.py` (not in gate) hangs on a live-ArangoDB graph sync — same out-of-scope category as live-AQL parity; skip it locally.
- `test_structural_fingerprint.py` freezes the graph column-node count; re-freezing the graph (SCHEMA_VERSION bump) requires updating that frozen count.
