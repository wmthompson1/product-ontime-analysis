SELECT 
    delivery_date,
    COUNT(*) as total_deliveries,
    AVG(ontime_rate) as avg_ontime_rate,
    SUM(actual_quantity) as units_delivered,
    SUM(planned_quantity) as units_planned,
    ROUND(100.0 * SUM(actual_quantity) / NULLIF(SUM(planned_quantity), 0), 1) as fulfillment_pct
FROM daily_deliveries
WHERE delivery_date >= date('now', '-7 days')
GROUP BY delivery_date
ORDER BY delivery_date DESC;
