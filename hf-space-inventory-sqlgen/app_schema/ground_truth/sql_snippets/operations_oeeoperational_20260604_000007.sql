-- OEE Operational: Equipment Utilization by Resource
-- Computes actual vs. scheduled run hours per active shop resource as an
-- OEE availability and performance proxy. Used for shift-level line
-- efficiency and operational throughput reporting.
SELECT
    sr.resource_id,
    sr.description,
    sr.resource_type,
    COUNT(op.rowid_pk)                           AS operation_count,
    ROUND(SUM(op.run_hrs), 2)                    AS scheduled_run_hrs,
    ROUND(SUM(op.act_run_hrs), 2)                AS actual_run_hrs,
    ROUND(SUM(op.setup_hrs), 2)                  AS scheduled_setup_hrs,
    ROUND(SUM(op.act_setup_hrs), 2)              AS actual_setup_hrs,
    CASE
        WHEN SUM(op.run_hrs) > 0
        THEN ROUND(SUM(op.act_run_hrs) / SUM(op.run_hrs), 4)
        ELSE NULL
    END                                           AS performance_ratio
FROM shop_resource sr
LEFT JOIN operation op ON op.resource_id = sr.resource_id
WHERE sr.active = 1
GROUP BY sr.resource_id, sr.description, sr.resource_type
ORDER BY performance_ratio DESC
