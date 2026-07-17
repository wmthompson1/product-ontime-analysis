---
name: Planned-order population carve-out
description: WO-PLN-* unreleased work orders are MRP proposals excluded from firm-order band and demand-linkage gates
---

Planned orders = `work_order` rows with `wo_id LIKE 'WO-PLN-%'`, status `unreleased` (user: planned = unreleased). They are MRP proposals, not demand-pegged firm supply.

**Rule:** any gate that counts work orders must decide which population it measures:
- Firm-order band [10,20] counts only `status IN ('firmed','released','closed')`.
- Demand-linkage layer (link backfill, forecast seeding, ratio gate, tests) excludes `WO-PLN-%` everywhere — including the migration's own fail-closed ratio denominator, or bootstrap re-runs fail after planned orders exist.

**Why:** unreleased WOs count as scheduled receipts in `mrp_engine.NONCLOSED_WO_STATUSES`, so planned orders must also avoid parts whose MRP grids are pinned by other fail-closed verifies (see PINNED_PARTS in the planned-orders migration).

**How to apply:** when adding synthetic work orders or new WO-counting gates, state the population (firm vs planned) explicitly and keep the WO-PLN exclusion consistent across migration verifies AND tests.
