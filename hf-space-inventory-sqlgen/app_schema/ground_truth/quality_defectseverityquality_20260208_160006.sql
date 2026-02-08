SELECT 
    severity_level,
    COUNT(*) AS incident_count,
    AVG(resolution_time_hours) AS avg_resolution_hours,
    SUM(cost_impact) AS total_cost_impact
FROM quality_incidents
WHERE incident_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY severity_level
ORDER BY incident_count DESC;
