---
name: Operation job-progress model
description: How job progress is represented in manufacturing.db (status/close_date, not sequence_no) and the idempotency rule for backfilling it.
---

# Operation job-progress model

Job progress for a work order is measured from `operation.status` (Q=Queued,
S=Started, C=Complete — UPPERCASE, matching schema + data) and
`operation.close_date`. It is NOT inferred from `operation.sequence_no`, which is a
gapped numeric routing-step ORDER only.

**Why:** the seeders left progress un-measurable — `operation.close_date` was never
written, `seed_erp_synthetic.py` forced every op to 'Q' even on Closed work orders,
and `add_purchasing_wip_tables.py` only marked ops 'C' when the whole WO was done
(else random Q/Q/S, unordered). A user asked for progress to be read from status /
close_date instead of sequence_no.

**Progress is derived from `work_order.status` + routing order**, not stored
independently. `work_order.status` uses the real planner vocabulary
(`unreleased`, `firmed`, `released`, `closed` — see wo-status-vocab.md):
unreleased/firmed → all 'Q' (not on the floor); closed → all 'C' with close_date;
released → a realistic SPREAD per WO via `crc32(wo_id)` RNG — some all-'Q'
(just released), most leading 'C' (with close_date) + exactly one 'S' + trailing 'Q',
some all-'C' (work done, awaiting close-out). Completed-op close_dates are spread in
routing order inside `[wo.open_date, end]` (`end` = `wo.close_date` for closed, else
`min(required_date, AS_OF)`), so every op closes on/before its work order. Keep status
UPPERCASE — do NOT introduce the informal lowercase 'c'.

**How to apply:**
- Any backfill/recompute of progress must use a data-derived AS_OF
  (`MAX(work_order.close_date)`), never wall-clock `today()`, or idempotency breaks
  (re-runs would drift released/in-process close_dates).
- Seed determinism uses `zlib.crc32(wo_id)` (process-stable), never builtin `hash()`.
- Generators intentionally still emit the inconsistent raw data + OLD status labels;
  the committed DB is finished by the migration chain (operation_type →
  regap/requirements → **relabel_work_order_status** → backfill_operation_progress),
  all idempotent and reading the live tables. relabel MUST run before backfill, since
  backfill keys progress off `work_order.status` (backfill also keeps the old labels
  as a fallback so the two are order-tolerant).
