---
name: Protected July throughput series & AS_OF re-anchor
description: WO-JUL-%/CO-JUL-% daily-cadence series is band-exempt; moving AS_OF requires re-running downstream anchor-dependent migrations AND pruning stale keyed rows.
---

# Protected July throughput series

The daily July 2026 throughput seed (`WO-JUL-01..31`, `CO-JUL-01`) is a protected synthetic series: it sits deliberately outside the demo-scale bands (CO/WO [10,20]) and keeps a fixed daily date cadence.

**Rules:**
- Every band count (prune, expand, demand-expansion verify, and their tests) must exclude `WO-JUL-%` / `CO-JUL-%`, same spirit as `WO-PLN-%`.
- Demand-date rewrites (`backfill_mrp_demand_supply`) must exempt `CO-JUL-%` lines or the daily cadence is destroyed.
- Any WO closed in the series must keep ALL activity (labor clock_in/out, material issue dates) strictly inside July — day-1 labor is clamped to Jul 1 08:00 or June month-end WIP reconciliation breaks.

**AS_OF re-anchor lesson:** shifting the data-derived AS_OF (MAX work_order.close_date) invalidates every anchor-derived artifact. Two failure modes seen:
1. Migrations that recompute on re-run still leave *stale keyed rows* behind (forecast rows keyed FC-part-YYYYMM from the old anchor sat outside the new horizon). Re-anchoring upserts must also PRUNE rows not in the recomputed set.
2. GL events are idempotent by (source_table, source_id, event_type) and never re-dated/re-amounted — after changing tickets/issues, delete the affected jobs' gl rows and re-run `backfill_gl_ledger.py`, or the ledger silently holds pre-change values.

**How to apply:** whenever a seed/migration moves AS_OF, re-run the full anchor chain in bootstrap order (seed → mrp backfill → mrp expand → demand linkage/forecast) and regenerate GL for touched jobs, then run the gate tests one file at a time.
