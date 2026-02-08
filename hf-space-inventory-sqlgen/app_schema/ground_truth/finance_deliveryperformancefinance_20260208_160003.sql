SELECT 
    strftime('%Y-%m', delivery_date) as month,
    COUNT(*) as total_deliveries,
    SUM(CASE WHEN ontime_rate < 0.95 THEN 1 ELSE 0 END) as late_deliveries,
    ROUND(100.0 * SUM(CASE WHEN ontime_rate < 0.95 THEN 1 ELSE 0 END) / COUNT(*), 1) as late_pct,
    SUM(CASE WHEN ontime_rate < 0.95 
        THEN (planned_quantity - actual_quantity) * 15.00
        ELSE 0 END) as penalty_amount,
    SUM(planned_quantity - actual_quantity) as total_shortage_units
FROM daily_deliveries
GROUP BY strftime('%Y-%m', delivery_date)
ORDER BY month DESC;
