SELECT 
    pl.line_name,
    pl.line_type,
    COUNT(ps.schedule_id) AS scheduled_runs,
    SUM(ps.target_quantity) AS total_target,
    SUM(ps.actual_quantity) AS total_actual,
    ROUND(AVG(ps.efficiency_score) * 100, 1) AS avg_efficiency_pct
FROM production_lines pl
LEFT JOIN production_schedule ps ON pl.line_id = ps.line_id
WHERE ps.planned_start >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY pl.line_id, pl.line_name, pl.line_type
ORDER BY avg_efficiency_pct DESC;
