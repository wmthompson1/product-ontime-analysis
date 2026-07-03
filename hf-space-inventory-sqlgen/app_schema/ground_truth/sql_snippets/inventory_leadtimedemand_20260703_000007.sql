/* Lead-Time Demand by Part */
/* Expected demand during the replenishment lead-time window:
   average daily demand (from open customer-order lines) multiplied by
   the part's lead_time_days. Shows whether each part's reorder point
   covers its lead-time exposure. */
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.lead_time_days,
    p.reorder_point,
    p.on_hand_qty,
    COALESCE(agg.total_demand, 0)                                            AS total_open_demand,
    COALESCE(agg.open_order_count, 0)                                        AS open_order_count,
    ROUND(
        COALESCE(agg.total_demand, 0) / NULLIF(agg.horizon_days, 0),
        4
    )                                                                        AS avg_daily_demand,
    ROUND(
        COALESCE(agg.total_demand, 0)
        / NULLIF(agg.horizon_days, 0)
        * p.lead_time_days,
        2
    )                                                                        AS lead_time_demand,
    CASE
        WHEN p.reorder_point >= ROUND(
            COALESCE(agg.total_demand, 0) / NULLIF(agg.horizon_days, 0)
            * p.lead_time_days, 2)
        THEN 'ROP_COVERS_LT_DEMAND'
        ELSE 'ROP_BELOW_LT_DEMAND'
    END                                                                      AS coverage_status
FROM part p
LEFT JOIN (
    SELECT
        part_id,
        SUM(order_qty)                                                       AS total_demand,
        COUNT(*)                                                             AS open_order_count,
        CAST(
            (JULIANDAY(MAX(need_by_date)) - JULIANDAY(MIN(need_by_date)) + 1)
        AS REAL)                                                             AS horizon_days
    FROM customer_order_line
    GROUP BY part_id
) agg ON agg.part_id = p.part_id
WHERE p.active = 1
ORDER BY lead_time_demand DESC
