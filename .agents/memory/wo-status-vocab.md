---
name: ERP planner vocabulary (supply + demand)
description: The user's real ERP status vocabulary for work orders (supply side) and order fulfillment (demand side) — what each term means and how synthetic data should model it.
---

# ERP planner vocabulary

The user is an aerospace-manufacturing planner. Use THEIR real ERP words in the
synthetic data, not invented ones. The seeders still emit older invented labels;
migrations relabel the committed DB onto these terms.

## Supply side — `work_order.status` (DONE / live)
Four planner statuses (`work_order.status` is free TEXT, no CHECK constraint):
- **unreleased** — planned, not yet released to the floor; no operation started.
- **firmed** — a firm planned order the planner has LOCKED (MRP won't reschedule it).
  Used for **first lots tested** and **recently engineered parts** (extra control
  before release). Still pre-release, so operations are all 'Q'.
- **released** — released to the floor; work in progress. Step-level progress is read
  from `operation.status`/`operation.close_date` (see operation-progress-model.md).
- **closed** — job finished and closed out.

In synthetic data, `firmed` is a deterministic subset of not-yet-released jobs
(`crc32(wo_id) % 4 == 0`) — NOT derived from real first-lot/engineering signals
(none exist in the synthetic schema). Honest stand-in, documented in the migration.

## Demand side — order fulfillment (DEFERRED — not yet built)
User FYI (not yet implemented). Order-fulfillment concepts:
- **shipped** — quantity already shipped to the customer.
- **allocated** — on-hand inventory committed/reserved against open demand.
- **available-to-promise (ATP)** = quantity on hand − allocated.

**Why:** captured so the deferred demand-side request isn't lost.
**How to apply:** if asked to model fulfillment, the `customer_order` table is the
demand anchor (seeder CO statuses were Open/Shipped/Closed/Cancelled); ATP is a
derived inventory measure (on-hand minus allocated), not a stored status. Confirm
scope with the user before building — they flagged it only as FYI.
