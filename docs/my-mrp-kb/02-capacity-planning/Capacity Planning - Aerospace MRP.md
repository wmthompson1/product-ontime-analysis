# Capacity Planning — Aerospace MRP (start with 1 shift)

## What this is

Capacity planning answers a simple question: **can the shop floor actually do all
the work that is scheduled, in the time available?**

It compares two numbers, work center by work center, week by week:

- **Load** — the work we have *asked* a work center to do (the standard setup +
  run hours of every operation routed through it).
- **Capacity** — the work a center *can* do in that time (its available hours).

If load fits inside capacity, the plan is realistic. If load is bigger than
capacity, that center is a **bottleneck** — it will run late unless we add time
(another shift), move work elsewhere, or pull the schedule apart.

We **start with 1 shift** as the baseline capacity (one 8-hour shift, 5 working
days a week = **40 hours per week** per work center) and see where that holds and
where it doesn't. Moving to 2 or 3 shifts is then a single number change.

This is the SQLite-grounded synthetic showcase. The runnable queries live in the
companion file **`manufacturing_capacityplanning_20260704_000001.sql`** (archived
under `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/`)
and all sample numbers below come from running them against `manufacturing.db`.

---

## The capacity model (the "1 shift" assumption)

The synthetic database stores the **work** (operations and their hours) but it
does **not** store a shop calendar, so available capacity is built from a few
explicit, editable assumptions at the top of every capacity query:

```sql
WITH params AS (
    SELECT 1 AS shifts, 8.0 AS hours_per_shift, 5 AS working_days_per_week
)
-- available hours per work center per week
--   = shifts × hours_per_shift × working_days_per_week
--   = 1 × 8 × 5 = 40 hours / week
```

To plan a second or third shift, change `shifts` to `2` or `3` and re-run — every
capacity number scales automatically. Keeping the assumption in plain sight (and
in code) is deliberate: the project rule is *explicit over silent*. We never hide
a capacity figure inside the query logic.

---

## How load is measured

- **Load basis = standard hours** (`operation.setup_hrs + operation.run_hrs`).
  This is the planning number — what the job *should* take — not what it actually
  took. (The actuals `act_setup_hrs` / `act_run_hrs` are a separate "what really
  happened" lens and are not used here.)
- **Where the load lands** = the week of the operation's `sched_start_date`. Each
  operation's hours are placed in its start week (rough-cut placement).
- **In-house only.** Outside-service operations (sent to a vendor) use no internal
  capacity, so only machine (`M`) and labor (`L`) work centers are loaded.

---

## Concept mapping (real ERP → synthetic SQLite)

| Real Infor VISUAL (SQL Server, reference only) | Synthetic stand-in (`manufacturing.db`, SQLite) |
|---|---|
| `SHOP_RESOURCE` (the work center) | `shop_resource` |
| `SHOP_RESOURCE.SHIFT_1_CAPACITY` (machines per shift) | *(none — assume 1 unit per resource)* |
| `SHOP_RESOURCE.EFFICIENCY_FACTOR` | *(none — assume 100% efficient)* |
| `SHIFT` (shift window definitions) | *(none — modeled by the `params` CTE)* |
| `CALENDAR_WEEK.SHIFT_1/2/3` (hours per day) | *(none — modeled by the `params` CTE)* |
| `CALENDAR_WEEK.SHIFT_x_CAPACITY` (unit counts) | *(none — assume 1 unit per resource)* |
| `OPERATION.SETUP_HRS` / `RUN_HRS` | `operation.setup_hrs` / `run_hrs` (standard) |
| `OPERATION.RESOURCE_ID` | `operation.resource_id` |
| `OPERATION.SCHED_START_DATE` | `operation.sched_start_date` (load bucket) |
| `OPERATION.STATUS` | `operation.status` (Q queued / S started / C closed) |

---

## Synthetic vs. real ERP (where the model is thinner)

| Topic | Real ERP | This synthetic model |
|---|---|---|
| Work calendar | `SHIFT` + `CALENDAR_WEEK` give per-resource, per-day hours | None — capacity is the `params` assumption (40 h/week at 1 shift) |
| Machines per resource | `SHIFT_x_CAPACITY` can stack N units on one resource | Each `resource_id` = **1** unit |
| Efficiency | `EFFICIENCY_FACTOR` derates available hours | Gross capacity, 100% efficient |
| Load placement | Finite scheduling spreads hours across start→finish | Hours placed in the **start week** only |
| Hours type | Per-piece (`PC`) vs per-hour (`HR`) routings | All operations are `HR` (total hours; no × quantity) |

These gaps are why the numbers below are a **rough-cut** capacity plan (a good
first pass to find bottlenecks), not a minute-by-minute finite schedule.

---

## Query 1 — Operation load register

The raw picture: one row per in-house operation with its work center, the week
its load lands in, and its standard hours. This feeds every view below.

Sample (the heaviest operations — each a 10-hour assembly step):

| resource_id | work_center | wo_id | seq | status | week_start | setup_hrs | run_hrs | load_hrs |
|---|---|---|---|---|---|---|---|---|
| LB-003 | Assembly Technician — Level II | WO-00052 | 40 | C | 2024-11-04 | 2.0 | 8.0 | 10.0 |
| LB-003 | Assembly Technician — Level II | WO-00059 | 100 | Q | 2024-02-26 | 2.0 | 8.0 | 10.0 |
| LB-003 | Assembly Technician — Level II | WO-00061 | 100 | S | 2025-03-10 | 2.0 | 8.0 | 10.0 |

---

## Query 2 — Weekly load vs 1-shift capacity, by work center

For each work center and week: total load hours vs the 40-hour capacity, the
utilization %, and an `OVER` flag if a single week's load exceeds one shift.

Sample (the busiest weeks across the whole horizon):

| resource_id | work_center | week_start | ops | load_hrs | capacity_hrs | utilization_pct | flag |
|---|---|---|---|---|---|---|---|
| LB-003 | Assembly Technician — Level II | 2024-02-12 | 2 | 20.0 | 40.0 | 50 | ok |
| LB-003 | Assembly Technician — Level II | 2025-09-29 | 2 | 20.0 | 40.0 | 50 | ok |
| ASSEM-LINE-2 | Assembly Line 2, Sub-Assembly | 2026-03-02 | 3 | 15.0 | 40.0 | 38 | ok |
| MC-003 | DMG Mori NHX 4000 HMC | 2024-02-12 | 2 | 12.0 | 40.0 | 30 | ok |
| ASSEM-LINE-1 | Assembly Line 1, Integration Bay | 2026-03-16 | 3 | 10.5 | 40.0 | 26 | ok |

The single busiest week anywhere in the plan reaches **50%** of one shift.

---

## Query 3 — Work-center bottleneck ranking at 1 shift

Rolls the weekly profile up to one row per work center: total load, the busiest
single week, peak utilization vs 1 shift, weeks over capacity, and a verdict. The
center with the highest peak utilization is the relative bottleneck — the one
with the least headroom. Here, even it stays well inside 1 shift, so it is a
*watch* item, not an actual constraint.

Sample (ranked by peak utilization):

| resource_id | work_center | type | active_weeks | total_load_hrs | peak_week_hrs | weekly_capacity_hrs | peak_util_pct | weeks_over | verdict |
|---|---|---|---|---|---|---|---|---|---|
| LB-003 | Assembly Technician — Level II | L | 17 | 190.0 | 20.0 | 40.0 | 50 | 0 | fits inside 1 shift |
| ASSEM-LINE-2 | Assembly Line 2, Sub-Assembly | L | 9 | 60.0 | 15.0 | 40.0 | 38 | 0 | fits inside 1 shift |
| MC-003 | DMG Mori NHX 4000 HMC | M | 17 | 114.0 | 12.0 | 40.0 | 30 | 0 | fits inside 1 shift |
| ASSEM-LINE-1 | Assembly Line 1, Integration Bay | L | 9 | 49.0 | 10.5 | 40.0 | 26 | 0 | fits inside 1 shift |
| CNC-MILL-1 | CNC Milling Cell #1, Haas VF-4 | M | 14 | 61.8 | 9.0 | 40.0 | 23 | 0 | fits inside 1 shift |

Every one of the 15 in-house work centers shows `weeks_over_capacity = 0`.

---

## Query 4 — Shifts required to clear the peak week (the scaling path)

Starting at 1 shift, this asks per work center: how many shifts would the busiest
week actually need? `shifts_required_at_peak = ceil(peak_week_hrs / 40)`.

Sample:

| resource_id | work_center | peak_week_hrs | one_shift_week_hrs | shifts_required_at_peak | recommendation |
|---|---|---|---|---|---|
| LB-003 | Assembly Technician — Level II | 20.0 | 40.0 | 1 | 1 shift is enough |
| ASSEM-LINE-2 | Assembly Line 2, Sub-Assembly | 15.0 | 40.0 | 1 | 1 shift is enough |
| MC-003 | DMG Mori NHX 4000 HMC | 12.0 | 40.0 | 1 | 1 shift is enough |
| ASSEM-LINE-1 | Assembly Line 1, Integration Bay | 10.5 | 40.0 | 1 | 1 shift is enough |
| CNC-MILL-1 | CNC Milling Cell #1, Haas VF-4 | 9.0 | 40.0 | 1 | 1 shift is enough |

Across all 15 work centers, `shifts_required_at_peak = 1`.

---

## The finding: at 1 shift, the shop has plenty of room

Over the whole scheduled horizon (Jan 2024 – May 2026): **15 in-house work
centers, 334 operations, 834.3 standard load hours.**

- **One shift covers everything.** No work center is over capacity in any week.
- **The busiest center is the Level-II Assembly Technician (LB-003)** — the
  relative bottleneck: the most loaded center (190 hours total) and the highest
  peak (20 hours in its busiest week = **50%** of one shift). It is *not* over
  capacity — simply the first place to watch if demand grows.
- **Even the peak week leaves ~50% headroom.** Load could roughly double in a peak
  week before the Assembly Technician needed a second shift.

In short: **start with 1 shift — and 1 shift is enough** for the current plan.
The center to keep an eye on is assembly labor (LB-003), not the machines — though
even it sits at only 50% in its busiest week.

### When you would add a shift

Re-run with `shifts = 2` (or `3`) in the `params` CTE to model more capacity, or
watch for these triggers at 1 shift:

- A work center shows `flag = 'OVER'` in **Query 2** (a week's load > 40 hours).
- `weeks_over_capacity > 0` or `shifts_required_at_peak > 1` for a center.
- Peak utilization (Query 3) climbing toward 100% — add the shift *before* it tips
  over, starting with the busiest center (assembly labor).

---

## How to run it

```bash
sqlite3 hf-space-inventory-sqlgen/app_schema/manufacturing.db \
    < "hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/manufacturing_capacityplanning_20260704_000001.sql"
```

All four queries are standard SQLite and read-only. Change the `params` CTE to
model different shift patterns; nothing else needs to change.
