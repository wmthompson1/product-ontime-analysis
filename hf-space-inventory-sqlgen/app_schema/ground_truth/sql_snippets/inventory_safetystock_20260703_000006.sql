/* Safety Stock Proxy by Part */
/* Safety stock = Reorder Point minus the estimated lead-time demand.
   Lead-time demand is derived from open customer-order quantities on file,
   averaged to a daily rate and scaled by each part's lead-time window.
   Negative safety_stock_proxy indicates the reorder point is understated
   relative to current demand exposure. */
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.reorder_point,
    p.lead_time_days,
    p.on_hand_qty,
    COALESCE(agg.total_demand, 0)                                            AS total_open_demand,
    COALESCE(agg.open_order_count, 0)                                        AS open_order_count,
    ROUND(
        COALESCE(agg.total_demand, 0)
        / NULLIF(agg.horizon_days, 0),
        4
    )                                                                        AS avg_daily_demand,
    ROUND(
        COALESCE(agg.total_demand, 0)
        / NULLIF(agg.horizon_days, 0)
        * p.lead_time_days,
        2
    )                                                                        AS lt_demand_proxy,
    ROUND(
        p.reorder_point
        - (COALESCE(agg.total_demand, 0) / NULLIF(agg.horizon_days, 0)
           * p.lead_time_days),
        2
    )                                                                        AS safety_stock_proxy,
    CASE
        WHEN (p.reorder_point
              - COALESCE(agg.total_demand, 0) / NULLIF(agg.horizon_days, 0)
                * p.lead_time_days) < 0
        THEN 'ROP_UNDERSTATED'
        WHEN (p.reorder_point
              - COALESCE(agg.total_demand, 0) / NULLIF(agg.horizon_days, 0)
                * p.lead_time_days) = 0
        THEN 'ZERO_BUFFER'
        ELSE 'ADEQUATE_BUFFER'
    END                                                                      AS rop_health
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
ORDER BY safety_stock_proxy ASC
