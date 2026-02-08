SELECT 
    equipment_name,
    equipment_type,
    measurement_date,
    ROUND(availability_rate * 100, 1) AS availability_pct,
    ROUND(performance_rate * 100, 1) AS performance_pct,
    ROUND(quality_rate * 100, 1) AS quality_pct,
    ROUND(oee_score * 100, 1) AS oee_pct,
    downtime_hours
FROM equipment_metrics
WHERE measurement_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY oee_score DESC;
