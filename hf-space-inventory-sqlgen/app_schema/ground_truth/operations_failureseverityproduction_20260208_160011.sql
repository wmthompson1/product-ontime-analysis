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
