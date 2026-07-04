/*
Capacity Planning — SQLite grounding query (SYNTHETIC). START WITH 1 SHIFT.

This is the runnable SQLite query set that grounds the companion document
"Capacity Planning - Aerospace MRP.md". It is rooted in the SUPPLY (shop-floor
work) perspective: each in-house `operation` carries standard work content
(setup + run hours) on a `shop_resource` (work center), and we compare that
LOAD against the AVAILABLE capacity of each work center.

Per project convention the synthetic target dialect is SQLite (manufacturing.db).
The real Infor VISUAL T-SQL (Live.dbo.SHOP_RESOURCE, SHIFT, CALENDAR_WEEK,
OPERATION) is a faithful reference benchmark ONLY — not the synthetic target.

Ground-truth (Live.dbo.*, T-SQL)          ->  stand-in (manufacturing.db, SQLite)
  SHOP_RESOURCE                             ->  shop_resource          (work center)
  SHOP_RESOURCE.SHIFT_1_CAPACITY            ->  (none — assumed 1 unit per resource)
  SHOP_RESOURCE.EFFICIENCY_FACTOR           ->  (none — assumed 100% efficient)
  SHIFT (shift window definitions)          ->  (none — modeled by the params CTE)
  CALENDAR_WEEK.SHIFT_1/2/3 (hrs/day)       ->  (none — modeled by the params CTE)
  CALENDAR_WEEK.SHIFT_x_CAPACITY (units)    ->  (none — assumed 1 unit per resource)
  OPERATION.RUN_HRS / SETUP_HRS             ->  operation.run_hrs / setup_hrs (standard)
  OPERATION.RESOURCE_ID                     ->  operation.resource_id  (FK shop_resource)
  OPERATION.SCHED_START_DATE                ->  operation.sched_start_date (load bucket)
  OPERATION.STATUS                          ->  operation.status (Q=queued, S=started, C=closed)

Join key: operation.resource_id = shop_resource.resource_id.

CAPACITY MODEL (the "start with 1 shift" assumption — edit the params CTE):
  available hours per work center per week
    = shifts (1) x hours_per_shift (8) x working_days_per_week (5)
    = 40 hours / week / work center.
  To plan a 2nd or 3rd shift, change `shifts` to 2 or 3 in the params CTE and
  re-run; every capacity number scales with it.

IMPORTANT — where the synthetic model is THINNER than the real ERP reference:
  * No SHIFT or CALENDAR_WEEK table — there is no stored per-resource work
    calendar, so available capacity is DERIVED from explicit assumption constants
    (params CTE), not read from a calendar.
  * No SHIFT_x_CAPACITY / machine-count column — each resource_id is treated as
    ONE capacity unit (one machine or one person). Real ERP can stack N units per
    shift on a single resource.
  * No EFFICIENCY_FACTOR — capacity here is GROSS (100% efficient). Real ERP
    derates available hours by an efficiency/utilization factor.
  * Load is placed in the week of the operation's sched_start_date; hours are NOT
    spread across the sched_start -> sched_finish span (rough-cut placement). Real
    finite scheduling spreads each operation's hours across the calendar.
  * Scheduled operations only: an operation with no sched_start_date has no week to
    land in, so it is excluded (it would otherwise fall into a NULL bucket). NULL
    setup/run hours are coalesced to 0 so one missing component never voids a load.
  * Planning load basis = STANDARD hours (setup_hrs + run_hrs). Actuals
    (act_setup_hrs / act_run_hrs) are a separate "what really happened" lens and
    are not used here. All operations are run_type='HR', so hours are total
    operation hours (no per-piece x quantity conversion is needed).
  * Outside-service operations (service_id IS NOT NULL, resource_type 'S') consume
    NO internal capacity and are excluded. Only in-house machine ('M') and labor
    ('L') work centers are loaded.
See the companion document's "Synthetic vs. real ERP" table for the full mapping.

A reusable note on the week bucket: SQLite has no ISO-week helper, so the Monday
that starts each operation's week is computed as
  date(sched_start_date, '-' || ((strftime('%w', sched_start_date) + 6) % 7) || ' days')
(%w returns 0=Sun..6=Sat; (%w + 6) % 7 = days elapsed since Monday).

----------------------------------------------------------------------
QUERY 1 — Operation load register (the raw load picture).
One row per in-house operation: its work center, the week its load lands in, the
standard setup/run hours, and the total load hours it puts on that work center.
This is the unaggregated input to every capacity view below.
----------------------------------------------------------------------
*/

SELECT
    o.resource_id,
    sr.description                                   AS work_center,
    sr.resource_type,
    o.wo_id,
    o.sequence_no,
    o.status,
    date(o.sched_start_date)                         AS sched_start,
    date(o.sched_start_date,
         '-' || ((CAST(strftime('%w', o.sched_start_date) AS INTEGER) + 6) % 7) || ' days')
                                                     AS week_start,
    ROUND(o.setup_hrs, 2)                            AS setup_hrs,
    ROUND(o.run_hrs, 2)                              AS run_hrs,
    ROUND(COALESCE(o.setup_hrs, 0) + COALESCE(o.run_hrs, 0), 2) AS load_hrs
FROM operation o
JOIN shop_resource sr
    ON sr.resource_id = o.resource_id
WHERE o.service_id IS NULL
  AND sr.resource_type IN ('M', 'L')
  AND o.sched_start_date IS NOT NULL
ORDER BY o.resource_id, week_start, o.wo_id, o.sequence_no;

/*
----------------------------------------------------------------------
QUERY 2 — Weekly load vs 1-shift capacity, by work center (the load profile).
For each work center and week, total the standard load hours and compare them to
the available capacity at 1 shift (40 h/week). utilization_pct = load / capacity.
flag = 'OVER' when a single week's load exceeds one shift's capacity.
----------------------------------------------------------------------
*/

WITH params AS (
    SELECT 1 AS shifts, 8.0 AS hours_per_shift, 5 AS working_days_per_week
),
weekly_load AS (
    SELECT
        o.resource_id,
        date(o.sched_start_date,
             '-' || ((CAST(strftime('%w', o.sched_start_date) AS INTEGER) + 6) % 7) || ' days')
                                                     AS week_start,
        COUNT(*)                                     AS ops,
        SUM(COALESCE(o.setup_hrs, 0) + COALESCE(o.run_hrs, 0)) AS load_hrs
    FROM operation o
    JOIN shop_resource sr
        ON sr.resource_id = o.resource_id
    WHERE o.service_id IS NULL
      AND sr.resource_type IN ('M', 'L')
      AND o.sched_start_date IS NOT NULL
    GROUP BY o.resource_id, week_start
)
SELECT
    wl.resource_id,
    sr.description                                   AS work_center,
    wl.week_start,
    wl.ops,
    ROUND(wl.load_hrs, 1)                            AS load_hrs,
    ROUND(p.shifts * p.hours_per_shift * p.working_days_per_week, 1)
                                                     AS capacity_hrs,
    ROUND(100.0 * wl.load_hrs
          / (p.shifts * p.hours_per_shift * p.working_days_per_week), 0)
                                                     AS utilization_pct,
    CASE WHEN wl.load_hrs > p.shifts * p.hours_per_shift * p.working_days_per_week
         THEN 'OVER' ELSE 'ok' END                   AS flag
FROM weekly_load wl
JOIN shop_resource sr
    ON sr.resource_id = wl.resource_id
CROSS JOIN params p
ORDER BY utilization_pct DESC, wl.week_start;

/*
----------------------------------------------------------------------
QUERY 3 — Work-center bottleneck ranking at 1 shift.
Roll the weekly profile up to one row per work center: total load over the
horizon, the busiest single week (peak_week_hrs), peak utilization against 1
shift, and how many weeks (if any) the load exceeds one shift. The verdict names
the situation: at 1 shift, which work centers strain and which have headroom.
The work center with the highest peak utilization is the relative bottleneck (the
one with the least headroom) — top-ranked does NOT mean it is over capacity.
----------------------------------------------------------------------
*/

WITH params AS (
    SELECT 1 AS shifts, 8.0 AS hours_per_shift, 5 AS working_days_per_week
),
weekly_load AS (
    SELECT
        o.resource_id,
        date(o.sched_start_date,
             '-' || ((CAST(strftime('%w', o.sched_start_date) AS INTEGER) + 6) % 7) || ' days')
                                                     AS week_start,
        SUM(COALESCE(o.setup_hrs, 0) + COALESCE(o.run_hrs, 0)) AS load_hrs
    FROM operation o
    JOIN shop_resource sr
        ON sr.resource_id = o.resource_id
    WHERE o.service_id IS NULL
      AND sr.resource_type IN ('M', 'L')
      AND o.sched_start_date IS NOT NULL
    GROUP BY o.resource_id, week_start
)
SELECT
    wl.resource_id,
    sr.description                                   AS work_center,
    sr.resource_type,
    COUNT(*)                                         AS active_weeks,
    ROUND(SUM(wl.load_hrs), 1)                       AS total_load_hrs,
    ROUND(MAX(wl.load_hrs), 1)                       AS peak_week_hrs,
    ROUND(p.shifts * p.hours_per_shift * p.working_days_per_week, 1)
                                                     AS weekly_capacity_hrs,
    ROUND(100.0 * MAX(wl.load_hrs)
          / (p.shifts * p.hours_per_shift * p.working_days_per_week), 0)
                                                     AS peak_util_pct,
    SUM(CASE WHEN wl.load_hrs > p.shifts * p.hours_per_shift * p.working_days_per_week
             THEN 1 ELSE 0 END)                      AS weeks_over_capacity,
    CASE WHEN MAX(wl.load_hrs) > p.shifts * p.hours_per_shift * p.working_days_per_week
         THEN 'strains 1 shift in peak week'
         ELSE 'fits inside 1 shift' END              AS verdict
FROM weekly_load wl
JOIN shop_resource sr
    ON sr.resource_id = wl.resource_id
CROSS JOIN params p
GROUP BY wl.resource_id
ORDER BY peak_util_pct DESC, total_load_hrs DESC;

/*
----------------------------------------------------------------------
QUERY 4 — Shifts required to clear the peak week (the scaling path).
Start at 1 shift and ask, per work center: how many shifts would the busiest week
actually need? shifts_required_at_peak = ceil(peak_week_hrs / one-shift-week).
SQLite has no CEIL, so we use integer truncation of (peak + capacity - epsilon).
This is the "do I need a 2nd/3rd shift, and only where?" decision view.
----------------------------------------------------------------------
*/

WITH params AS (
    SELECT 1 AS shifts, 8.0 AS hours_per_shift, 5 AS working_days_per_week
),
weekly_load AS (
    SELECT
        o.resource_id,
        date(o.sched_start_date,
             '-' || ((CAST(strftime('%w', o.sched_start_date) AS INTEGER) + 6) % 7) || ' days')
                                                     AS week_start,
        SUM(COALESCE(o.setup_hrs, 0) + COALESCE(o.run_hrs, 0)) AS load_hrs
    FROM operation o
    JOIN shop_resource sr
        ON sr.resource_id = o.resource_id
    WHERE o.service_id IS NULL
      AND sr.resource_type IN ('M', 'L')
      AND o.sched_start_date IS NOT NULL
    GROUP BY o.resource_id, week_start
),
peak AS (
    SELECT resource_id, MAX(load_hrs) AS peak_hrs
    FROM weekly_load
    GROUP BY resource_id
)
SELECT
    pk.resource_id,
    sr.description                                   AS work_center,
    ROUND(pk.peak_hrs, 1)                            AS peak_week_hrs,
    ROUND(p.hours_per_shift * p.working_days_per_week, 1)
                                                     AS one_shift_week_hrs,
    -- exact ceil(peak / one-shift-week): floor(...) + 1 only if there is any remainder
    CAST(pk.peak_hrs / (p.hours_per_shift * p.working_days_per_week) AS INTEGER)
        + (pk.peak_hrs >
           CAST(pk.peak_hrs / (p.hours_per_shift * p.working_days_per_week) AS INTEGER)
           * (p.hours_per_shift * p.working_days_per_week))
                                                     AS shifts_required_at_peak,
    CASE
        WHEN pk.peak_hrs <= p.hours_per_shift * p.working_days_per_week
            THEN '1 shift is enough'
        WHEN pk.peak_hrs <= 2 * p.hours_per_shift * p.working_days_per_week
            THEN 'add a 2nd shift in the peak week'
        ELSE 'needs 3 shifts / offload in the peak week'
    END                                              AS recommendation
FROM peak pk
JOIN shop_resource sr
    ON sr.resource_id = pk.resource_id
CROSS JOIN params p
ORDER BY shifts_required_at_peak DESC, peak_week_hrs DESC;
