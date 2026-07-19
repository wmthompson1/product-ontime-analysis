# Synthetic Posting Functions (No Control Logic)

## What & Why
Implement the four simple posting functions from the PM plan — `post_material_issue`, `post_labor`, `post_overhead`, `post_job_completion` — each inserting a row into the relevant ledger table and `gl_job_cost_detail`/`gl_events`, with no period close, reconciliation, or validation. Then backfill the ledger deterministically from existing operational data so the tables tell the real job-costing story.

## Done looks like
- A posting module exposes the four functions; each is deterministic and testable (insert rows, update the relevant inventory table balance semantics — material out of raw materials into WIP, labor/overhead into WIP, completion out of WIP into finished goods).
- A backfill migration replays existing `material_issue`, `labor_ticket` (labor + burden as overhead), and closed `work_order` rows through these functions with idempotency keys (source document type + id), so re-runs create no duplicates.
- Job completion posts at the WO's `close_date`; planned orders (WO-PLN-*) and non-closed WOs are never completed.
- Per-job WIP totals tie to `work_order.act_lab_cost`/`act_bur_cost`/`act_mat_cost` for costs sourced from these documents; the backfill fails closed on drift with named offenders.
- Wired into the bootstrap chain after the table migration; a gate-style test (`python file.py`) exercises the functions.

## Out of scope
- RDF event emission (Task 5 adds that on top).
- Outside-service/procurement postings unless trivially covered by post_overhead.

## Steps
1. **Posting module** — four functions with a shared insert helper and idempotency-key support.
2. **Deterministic backfill** — replay operational history through the functions; wire into bootstrap chain.
3. **Tie-out + test** — per-WO reconciliation check against work_order actuals and a gate-style test file.

## Relevant files
- `hf-space-inventory-sqlgen/migrations/backfill_labor_chain.py`
- `hf-space-inventory-sqlgen/migrations/rebuild_clean_db.py`
- `hf-space-inventory-sqlgen/tests/`
