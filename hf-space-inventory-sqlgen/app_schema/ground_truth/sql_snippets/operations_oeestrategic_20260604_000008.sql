-- OEE Strategic: Capital Planning Resource Efficiency
-- Aggregates cost efficiency and utilization per shop resource type to
-- support capital investment, capacity planning, and equipment replacement
-- decisions. Surfaces cost-per-actual-run-hour as the strategic OEE proxy.
SELECT
    sr.resource_type,
    COUNT(DISTINCT sr.resource_id)                         AS resource_count,
    ROUND(SUM(op.run_hrs), 2)                              AS total_scheduled_hrs,
    ROUND(SUM(op.act_run_hrs), 2)                          AS total_actual_hrs,
    ROUND(SUM(op.act_atl_lab_cost + op.act_atl_bur_cost), 2) AS total_actual_cost,
    CASE
        WHEN SUM(op.act_run_hrs) > 0
        THEN ROUND(
            SUM(op.act_atl_lab_cost + op.act_atl_bur_cost) / SUM(op.act_run_hrs), 2
        )
        ELSE NULL
    END                                                     AS cost_per_actual_hr,
    CASE
        WHEN SUM(op.run_hrs) > 0
        THEN ROUND(SUM(op.act_run_hrs) / SUM(op.run_hrs), 4)
        ELSE NULL
    END                                                     AS utilization_ratio
FROM shop_resource sr
LEFT JOIN operation op ON op.resource_id = sr.resource_id
WHERE sr.active = 1
GROUP BY sr.resource_type
ORDER BY total_actual_cost DESC
