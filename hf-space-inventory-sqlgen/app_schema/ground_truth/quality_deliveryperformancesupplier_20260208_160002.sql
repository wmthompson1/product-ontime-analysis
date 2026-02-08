SELECT 
    s.supplier_name,
    COUNT(d.delivery_id) as total_deliveries,
    ROUND(AVG(d.ontime_rate), 3) as avg_ontime_rate,
    ROUND(AVG(d.quality_score), 3) as avg_quality_score,
    SUM(d.actual_quantity) as total_units,
    MIN(d.delivery_date) as first_delivery,
    MAX(d.delivery_date) as last_delivery
FROM daily_deliveries d
JOIN suppliers s ON d.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.supplier_name
ORDER BY avg_ontime_rate DESC;
