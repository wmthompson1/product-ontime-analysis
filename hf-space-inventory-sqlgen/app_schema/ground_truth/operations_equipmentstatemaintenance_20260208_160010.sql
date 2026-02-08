SELECT 
    downtime_category,
    COUNT(*) AS event_count,
    SUM(downtime_duration_minutes) AS total_downtime_mins,
    ROUND(AVG(downtime_duration_minutes), 0) AS avg_downtime_mins,
    SUM(production_loss_units) AS total_production_loss,
    SUM(cost_impact) AS total_cost_impact
FROM downtime_events
WHERE event_start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY downtime_category
ORDER BY total_downtime_mins DESC;
