# 100+ parts in the MRP dropdown

## What & Why
The MRP Schedule tab's part dropdown lists only parts that have open customer-order demand inside the 6-month planning horizon. Today that's just 2 parts: the database has 55 parts total, but only 1 customer order is still "Open" (2 lines / 2 distinct parts). The user wants at least 100 selectable parts so the MRP grid demo feels like a real plant. That requires expanding the synthetic data foundation: ~50+ new parts in the part master, plus open in-horizon demand and a valid supply basis for at least 100 distinct parts.

## Done looks like
- The MRP Schedule dropdown lists at least 100 parts.
- Every listed part computes a valid MRP grid (no fail-closed errors): positive lead time, on-hand quantity, and a real supply basis (open PO for BUY parts, open WO for MAKE parts, etc.).
- `validate_planning_inputs` still passes on the whole DB, and `scripts/bootstrap_db.py` on a fresh clone reproduces the same ≥100-part state (the expansion must be baked into the migration chain, not applied only to the live DB).
- All new data is deterministic (seeded from stable keys, e.g. the existing crc32 pattern) — same result on every re-run, idempotent.

## Out of scope
- Changing which parts qualify for the dropdown (keep the "open in-horizon demand" rule).
- Multi-level BOM explosion or any change to the netting logic in `mrp_engine.py`.
- Touching the ArangoDB graph, ground-truth snippets, or real-source reference files.
- The separately proposed demand-linkage / 3-month horizon-extension work (Task #244); if that lands first, the new demand rows should follow whatever linkage conventions it introduces.

## Steps
1. **Expand the part master** — Add a new deterministic, idempotent migration that grows the part table to well over 100 parts (aerospace-flavored part numbers, mixed part classes: MAKE / BUY / HARDWARE / RAW / OUTSIDE_SERVICE), each with a positive lead time, on-hand quantity, and planner/parts-master rows consistent with existing backfills.

2. **Seed open in-horizon demand** — In the same migration, create synthetic open customer orders and order lines so at least 100 distinct parts have `need_by_date` inside the planning horizon, using the data-derived AS_OF anchor (never wall-clock) and the crc32-style deterministic date placement already used by the MRP backfill.

3. **Guarantee a supply basis per part** — Ensure every new demand part passes the fail-closed planning validation: open POs for purchased parts and open WOs for manufactured parts (reuse/extend the existing fallback-PO pattern), without disturbing supplier scorecard or on-time-delivery history (only touch new synthetic rows).

4. **Wire into the rebuild chain and verify** — Register the migration in `bootstrap_db.py`'s chain in the right order, run it on the live DB, and confirm: dropdown count ≥100, a sampling of new parts renders correct grids in the UI, `validate_planning_inputs` passes, re-running the migration is a no-op, and the MRP tests plus the bootstrap MRP readiness check still pass (update the tests' expectations if they assume a tiny part count).

## Relevant files
- `hf-space-inventory-sqlgen/mrp_engine.py:187-296`
- `hf-space-inventory-sqlgen/migrations/backfill_mrp_demand_supply.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/migrations/backfill_pn_parts_master_and_planner.py`
- `hf-space-inventory-sqlgen/tests/test_mrp_schedule.py`
- `hf-space-inventory-sqlgen/app.py`
