SELECT 
    s.supplier_name,
    s.certification_level,
    ROUND(AVG(d.quality_score), 2) AS avg_quality,
    ROUND(AVG(d.ontime_rate) * 100, 1) AS ontime_pct,
    COUNT(CASE WHEN d.quality_score >= 0.95 THEN 1 END) AS excellent_deliveries,
    COUNT(CASE WHEN d.quality_score < 0.80 THEN 1 END) AS poor_deliveries
FROM suppliers s
JOIN daily_deliveries d ON s.supplier_id = d.supplier_id
WHERE d.delivery_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY s.supplier_id, s.supplier_name, s.certification_level
HAVING COUNT(d.delivery_id) >= 5
ORDER BY avg_quality DESC, ontime_pct DESC;
