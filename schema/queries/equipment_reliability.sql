-- Ground Truth SQL: Equipment Reliability Queries
-- Source: Flask Manufacturing App (LangChain Semantic Layer)
-- Category: Equipment & Maintenance Analytics

-- Query: Overall Equipment Effectiveness (OEE)
-- Description: Calculate OEE metrics by equipment
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

-- Query: Downtime Analysis by Category
-- Description: Aggregate downtime events by category
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

-- Query: Equipment Failure Analysis (MTBF)
-- Description: Mean Time Between Failures analysis
SELECT 
    e.equipment_name,
    COUNT(f.failure_id) AS failure_count,
    SUM(f.downtime_hours) AS total_downtime,
    AVG(f.repair_cost) AS avg_repair_cost,
    AVG(f.mtbf_impact) AS avg_mtbf_hours
FROM equipment_metrics e
LEFT JOIN failure_events f ON e.equipment_id = f.equipment_id
WHERE f.failure_date >= CURRENT_DATE - INTERVAL '180 days'
GROUP BY e.equipment_id, e.equipment_name
HAVING COUNT(f.failure_id) >= 1
ORDER BY failure_count DESC;
