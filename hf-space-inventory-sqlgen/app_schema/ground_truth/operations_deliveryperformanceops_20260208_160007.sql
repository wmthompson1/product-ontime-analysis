SELECT 
    s.supplier_id,
    s.supplier_name,
    s.performance_rating,
    s.certification_level,
    COUNT(d.delivery_id) AS total_deliveries,
    AVG(d.ontime_rate) AS avg_ontime_rate,
    AVG(d.quality_score) AS avg_quality_score
FROM suppliers s
LEFT JOIN daily_deliveries d ON s.supplier_id = d.supplier_id
WHERE d.delivery_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.supplier_id, s.supplier_name, s.performance_rating, s.certification_level
ORDER BY avg_ontime_rate DESC;
