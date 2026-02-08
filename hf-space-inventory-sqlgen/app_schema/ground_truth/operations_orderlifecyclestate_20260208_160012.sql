SELECT 
    line_id,
    product_line,
    planned_start,
    actual_start,
    target_quantity,
    actual_quantity,
    ROUND((actual_quantity::numeric / NULLIF(target_quantity, 0)) * 100, 1) AS completion_pct,
    efficiency_score
FROM production_schedule
WHERE planned_start >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY planned_start DESC;
