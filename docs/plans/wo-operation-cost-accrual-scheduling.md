# Operation cost accrual & WO scheduling

## What & Why
Make the synthetic `manufacturing.db` data faithfully reflect the real ERP job-costing flow: a work order is scheduled with a start date, each operation is released and accrues cost, and when an operation closes the next routing sequence can begin. Today the SQLite model can *express* most of this but the data doesn't live up to it — there is no work-order scheduled start/finish date at all, operation schedules don't chain (the next step is scheduled to start before the prior step closes), operation-level actual costs are all `0.0`, and ~40% of work orders have no operation scheduling whatsoever.

All work targets the **synthetic SQLite dialect only**. The real SQL Server `dbo.WORK_ORDER` / `dbo.WORK_ORDER_SCHED` DDL in `ddl/` is a faithful reference benchmark for column naming and intent — never the target dialect, and we are NOT introducing a separate scheduling table (scheduling stays as columns on `work_order`, mirroring how `operation` already carries `sched_start_date`/`sched_finish_date`).

**Costing method: actual costing (not standard costing).** Operation cost accrual is driven by *actual* transactions — actual labor tickets, actual hours worked, and actual outside-service receipts — and flows bottom-up from operation to work order. The estimated/standard columns (`est_atl_*`, `setup_hrs`, `run_hrs`) remain as the planning reference but are **never** used to compute the accrued actuals.

## Done looks like
- `work_order` carries scheduled dates (a scheduled start and finish, plus a release/desired-release anchor), populated for every work order, modeled on the real `dbo.WORK_ORDER` columns (`SCHED_START_DATE`, `SCHED_FINISH_DATE`, `DESIRED_RLS_DATE`).
- Every work order's operations form a coherent routing chain: each sequence's scheduled start falls on/after the previous sequence's close, in `sequence_no` order, for **both** the `WO-24xxxx` and the `WO-000xx` cohorts (no NULL operation schedules left).
- Operation-level actual costs (`act_atl_lab_cost`, `act_atl_bur_cost`, and outside-service `act_atl_ser_cost`) are populated from actual transactions and roll up consistently to the `work_order.act_*` totals — the per-operation actuals are no longer all zero, and the actual-cost figures are derived from actual hours/tickets, not from standard rates.
- The work order's scheduled start equals the earliest operation start and the scheduled finish equals the latest operation finish (the WO window is derived from its routing).
- All schema additions live in the seed/DDL source so a from-scratch rebuild carries them, and a re-run of the data backfills is deterministic and idempotent (no wall-clock, no randomness drift).
- `scripts/post-merge.sh` stays fully green — including the field-description coverage gate, the SQL-vs-file and SQL-vs-AQL parity gates, and the existing test suite.

## Out of scope
- Production **capacity** modeling (resource shift capacity, operation capacity usage, finite/load-vs-capacity scheduling) — a separate, larger effort; not included here.
- A dedicated `WORK_ORDER_SCHED` table — scheduling stays as columns on `work_order`.
- Adding estimated/remaining cost buckets to the work order beyond what already exists (`work_order` keeps its `act_*` rollups; no new `est_*`/`rem_*` columns).
- Standard costing / variance analysis (standard-vs-actual). Standard/estimated columns stay as a planning reference but are not used to drive accrual here.
- Any change to the real SQL Server reference files in `ddl/` or `attached_assets/`.

## Steps
1. **Add work-order scheduled-date columns to the synthetic schema.** Add a scheduled start, scheduled finish, and a release/desired-release date to `work_order` in the SQLite DDL source so a rebuild and the boot self-heal carry them. Use names aligned with the real `dbo.WORK_ORDER` reference. These are new physical columns on a table that is already represented in the graph, so they will become new graph column nodes — Step 5 handles that ripple.

2. **Regenerate operation schedules so the routing chains correctly.** Replace the placeholder per-sequence date stepping with a deterministic schedule where, within each work order ordered by `sequence_no`, each operation's scheduled start is on/after the prior operation's close (or finish), and each operation's duration is derived from its hours (`setup_hrs` + `run_hrs`, with a deterministic default where hours are missing). Cover **both** WO cohorts, including the `WO-000xx` work orders whose operation schedules are currently NULL. Follow the established backfill conventions: data-derived AS-OF (e.g. anchored on existing work-order dates / `MAX(work_order.close_date)`), per-WO randomness seeded by a stable crc32 of `wo_id`, fully idempotent — never wall-clock time, never `random.random()` without a stable seed.

3. **Derive the work-order scheduled window and release date from its routing.** Set each work order's scheduled start to the earliest operation start and scheduled finish to the latest operation finish, and set the release/desired-release date consistently with when the order's operations begin accruing (released orders anchored on/before their first started operation). Keep it consistent with the existing planner status vocabulary (`unreleased` / `firmed` / `released` / `closed`).

4. **Backfill operation-level cost accrual using actual costing (bottom-up).** Accrue per-operation actual labor and burden (`act_atl_lab_cost`, `act_atl_bur_cost`) from *actual* `labor_ticket` records aggregated to the `(wo_id, sequence_no)` grain, and per-operation outside-service actuals (`act_atl_ser_cost`) from the actual outside-service receipt/invoice flow tied to the operation. Populate the operation's actual hours (`act_setup_hrs`, `act_run_hrs`) from the same actual labor records so actual hours and actual cost stay consistent. Then recompute each `work_order.act_lab_cost` / `act_bur_cost` / `act_ser_cost` rollup as the **sum of its operations' actuals** (actuals flow up from transactions → operation → work order), rather than treating the existing WO totals as fixed. Do **not** use standard costing — never derive accrued actuals from `est_atl_*` or from standard rates × standard `setup_hrs`/`run_hrs`. Only accrue on operations that have progressed (started/closed), consistent with the operation status model; an operation with no actual transactions accrues no actual cost. Keep it deterministic and idempotent.

5. **Update the graph, coverage, and parity artifacts in lockstep.** Because the new `work_order` columns become graph column nodes, regenerate the `sql_graph_*` tables and re-freeze `graph_metadata.json` to the next SCHEMA_VERSION (v18), add the new rows to `field_descriptions.csv` so the field-description coverage gate matches exactly (it currently asserts 223/223 with no extras), and re-run the SQL-vs-file and SQL-vs-AQL parity checkers. Add/extend tests as needed so the new columns and the new backfills are covered, and confirm the whole `scripts/post-merge.sh` gate passes.

6. **Slot the new backfills into the documented migration run order.** The synthetic data pipeline runs the seeder then a documented chain of migrations (status relabel → operation progress → …). Place the new schedule-regeneration and cost-accrual steps in the correct order relative to `relabel_work_order_status.py` and `backfill_operation_progress.py` (operation status/close dates must exist before schedules chain off closes and before costs accrue on closed steps), and document the run order alongside the existing migrations.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/app_schema/schema.sql`
- `hf-space-inventory-sqlgen/scripts/seed_erp_synthetic.py:281-360,587-624`
- `hf-space-inventory-sqlgen/migrations/backfill_operation_progress.py`
- `hf-space-inventory-sqlgen/migrations/relabel_work_order_status.py`
- `hf-space-inventory-sqlgen/migrations/backfill_supplier_rating_and_wo_actuals.py`
- `ddl/dbo.WORK_ORDER.sql:13-47`
- `ddl/dbo.WORK_ORDER_SCHED.sql`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/sql_graph_tables.sql`
- `replit_integrations/seed_field_descriptions.py`
- `replit_integrations/field_description_coverage_check.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `field_descriptions.csv`
- `hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py`
- `hf-space-inventory-sqlgen/tests/test_sql_graph_tables.py`
- `scripts/post-merge.sh`
