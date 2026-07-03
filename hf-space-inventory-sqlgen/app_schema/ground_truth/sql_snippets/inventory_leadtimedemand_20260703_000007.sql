/* Lead-Time Demand by Part — set-aware, horizon-anchored */
/* Expected demand during the replenishment lead-time window:
   average daily demand x the part's lead_time_days.
   Set semantics (per docs/mrp_set_semantics_criteria.md):
     * Demand basis: ONLY customer_order.status = 'Open' lines whose need_by_date
       falls inside the planning horizon.  Closed / Shipped / Cancelled orders
       are excluded.
     * Denominator: a STABLE, shared horizon length in days derived from the
       data-anchored as-of date (AS_OF = MAX(work_order.close_date);
       PLAN_START = first of that month; horizon = PLAN_START + 6 months).
       This replaces the old per-part MAX(need_by_date)-MIN(need_by_date) window,
       which made avg_daily_demand incomparable across parts (a single-line part
       divided by 1 day, a multi-line part by its own spread).
   Shows whether each part's reorder point covers its lead-time exposure. */
WITH horizon AS (
    SELECT
        date(COALESCE((SELECT MAX(close_date) FROM work_order), '2026-06-12'),
             'start of month')                                          AS plan_start,
        date(date(COALESCE((SELECT MAX(close_date) FROM work_order), '2026-06-12'),
             'start of month'), '+6 months')                           AS horizon_end
),
open_demand AS (
    SELECT col.part_id,
           SUM(col.order_qty) AS total_demand,
           COUNT(*)           AS open_line_count
    FROM customer_order_line col
    JOIN customer_order o ON o.order_id = col.order_id
    CROSS JOIN horizon h
    WHERE o.status = 'Open'
      AND col.need_by_date IS NOT NULL
      AND date(col.need_by_date) >= h.plan_start
      AND date(col.need_by_date) <  h.horizon_end
    GROUP BY col.part_id
)
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.lead_time_days,
    p.reorder_point,
    p.on_hand_qty,
    COALESCE(od.total_demand, 0)                                        AS total_open_demand,
    COALESCE(od.open_line_count, 0)                                     AS open_line_count,
    CAST(julianday(h.horizon_end) - julianday(h.plan_start) AS REAL)    AS horizon_days,
    ROUND(
        COALESCE(od.total_demand, 0)
        / NULLIF(julianday(h.horizon_end) - julianday(h.plan_start), 0),
        4
    )                                                                  AS avg_daily_demand,
    CASE
        WHEN p.lead_time_days IS NULL OR p.lead_time_days <= 0 THEN NULL
        ELSE ROUND(
            COALESCE(od.total_demand, 0)
            / NULLIF(julianday(h.horizon_end) - julianday(h.plan_start), 0)
            * p.lead_time_days,
            2)
    END                                                                AS lead_time_demand,
    -- Fail-closed (criteria §2.3): a part with a missing / non-positive lead
    -- time cannot be planned, so we NEVER silently classify it as covered.
    CASE
        WHEN p.lead_time_days IS NULL OR p.lead_time_days <= 0
        THEN 'INVALID_LEAD_TIME'
        WHEN p.reorder_point >= ROUND(
            COALESCE(od.total_demand, 0)
            / NULLIF(julianday(h.horizon_end) - julianday(h.plan_start), 0)
            * p.lead_time_days, 2)
        THEN 'ROP_COVERS_LT_DEMAND'
        ELSE 'ROP_BELOW_LT_DEMAND'
    END                                                                AS coverage_status
FROM part p
CROSS JOIN horizon h
LEFT JOIN open_demand od ON od.part_id = p.part_id
WHERE p.active = 1
ORDER BY lead_time_demand DESC
