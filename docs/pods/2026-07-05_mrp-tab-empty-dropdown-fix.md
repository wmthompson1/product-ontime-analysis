# MRP Tab Empty Dropdown — Diagnosis & Fix

**Date:** 2026-07-05
**Context:** Fresh-clone validation of `product-ontime-analysis` (user's clone). After bootstrap failures earlier in the chain, the MRP Schedule tab showed an empty planning-part dropdown with the banner "MRP data foundation not found."

## Diagnosis

- The MRP dropdown is built **once at app startup** (`app.py`, MRP tab construction). At boot the app calls `mrp.list_planning_parts()`, `compute_as_of()`, and `month_buckets()`; any exception or empty result falls back to the "foundation not found" banner and a blank dropdown.
- The user's app had booted against a database where the bootstrap chain stopped partway (at the receiving-line step, before the earlier fixes), so the MRP demand/supply foundation was never built.
- This was **not a new bug** — just leftover state from the interrupted bootstrap plus a stale app process.

## Fix flow (user's machine)

1. Pull the latest (Faker removal, self-healing receiving-line migration, updated banner text).
2. Run the MRP backfill (or the full one-command bootstrap):
   - `python migrations/backfill_mrp_demand_supply.py` — user ran this ("result 2"), completed with:
     - as-of date: **2026-06-18** (data-derived)
     - horizon: **Jun 2026 .. Nov 2026**
     - open CO lines: **19**
     - outside-service WOs enriched: **6**
     - fail-closed validation: **PASS**
   - or `python scripts/bootstrap_db.py` — idempotent full rebuild ending in "MRP OK — N planning parts".
3. **Restart the app** — the dropdown only populates on a fresh boot.

## Repo change made

- `hf-space-inventory-sqlgen/app.py`: the "MRP data foundation not found" banner now points to `python scripts/bootstrap_db.py` (one-command rebuild) + app restart, instead of the single backfill migration — the bootstrap script is the supported repair path for fresh clones.

## Related side fixes this session

- Gradio "Connection to the server was lost" toast = normal after a workflow restart; just reload the frame.
- Removed the mockup preview server's root-forwarding rule (it 302'd `/` to the app on `:5000`); the mockup server root now goes to its own `/__mockup/` preview index. App URLs must carry `:5000`.
