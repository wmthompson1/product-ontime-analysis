# Monthly Orders vs Completed Orders — Customer-Perspective Governed View

**Date:** 2026-07-04
**Context:** Management request (Customer perspective): report monthly orders
compared to monthly completed orders, not aggregated, for 2025-01-01 to
2025-12-31. No existing governed view — the SME had to write one. Lineage:
started as a bar chart, so the shape is monthly time buckets.

---

## The gap

The synthetic ERP knew *that* orders completed (status `Shipped`/`Closed`)
but not *when* — no completion date anywhere. A monthly "completed" series
has nothing to bucket on without one.

## The fix (deterministic, no randomness)

Migration `hf-space-inventory-sqlgen/migrations/add_customer_order_completed_date.py`
adds `customer_order.completed_date` and backfills it for Shipped/Closed
orders as `order_date + MAX(lead_time_days)` across the order's lines — the
longest-lead part paces the order, which is exactly how an ERP projects
completion. Open/Cancelled stay NULL, and the migration fails closed if any
completed order would end up dateless. 37 orders backfilled.

## The governed view

`hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/customer_monthlyorderscompleted_20260704_000006.sql`

- One row per month, Jan–Dec 2025, zero-months included (a recursive month
  spine, so bar-chart buckets never vanish)
- Two series per bucket:
  - `orders_placed` — by order date, all statuses (it was an order when placed)
  - `orders_completed` — Shipped/Closed by completion date, regardless of
    when placed
- Date filters wrapped in `date(...)` so the view stays correct even if
  timestamp values ever land in those columns
- Header documents the request, the bar-chart lineage, and both definitions

## Verified result (manufacturing.db)

| Month   | Placed | Completed |
|---------|--------|-----------|
| 2025-01 | 1      | 0         |
| 2025-02 | 5      | 0         |
| 2025-03 | 3      | 1         |
| 2025-04 | 1      | 2         |
| 2025-05 | 1      | 0         |
| 2025-06 | 3      | 1         |
| 2025-07 | 5      | 2         |
| 2025-08 | 1      | 0         |
| 2025-09 | 1      | 2         |
| 2025-10 | 1      | 2         |
| 2025-11 | 6      | 2         |
| 2025-12 | 1      | 0         |

Placed sums to 29 — exactly the 2025 order count, so nothing is dropped or
double-counted. Some completions fall outside 2025 (late-2024 orders
finishing early, late-2025 orders finishing in 2026), which is realistic.

## Status

Code-reviewed and verified. The view is **not yet registered** in
`reviewer_manifest.json` — that is the SME sign-off step. After approval,
run it through `register_snippet.py` so it gets a structural fingerprint and
comes under SolderEngine governance like the other approved views.
