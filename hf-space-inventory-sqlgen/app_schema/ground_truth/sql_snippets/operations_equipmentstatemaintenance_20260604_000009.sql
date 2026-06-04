-- Equipment State: Maintenance Scheduling View
-- Shows each active shop resource with its open-operation count,
-- remaining scheduled run hours, and last close date.
-- Used by maintenance scheduling to identify resources due for preventive
-- maintenance or currently blocked by open operations.
SELECT
    sr.resource_id,
    sr.description,
    sr.resource_type,
    COUNT(
        CASE WHEN op.status NOT IN ('C', 'Closed') AND op.status IS NOT NULL
             THEN 1 END
    )                                                      AS open_operations,
    ROUND(
        SUM(
            CASE WHEN op.status NOT IN ('C', 'Closed')
                 THEN op.run_hrs - op.act_run_hrs
                 ELSE 0 END
        ), 2
    )                                                      AS remaining_run_hrs,
    MAX(op.close_date)                                     AS last_close_date,
    MAX(op.sched_finish_date)                              AS next_sched_finish
FROM shop_resource sr
LEFT JOIN operation op ON op.resource_id = sr.resource_id
WHERE sr.active = 1
GROUP BY sr.resource_id, sr.description, sr.resource_type
ORDER BY open_operations DESC, remaining_run_hrs DESC
