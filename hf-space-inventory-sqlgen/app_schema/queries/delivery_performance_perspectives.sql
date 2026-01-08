-- Ground Truth SQL: Delivery Performance by Perspective
-- Demonstrates semantic disambiguation via organizational perspective
-- Same field (daily_deliveries.ontime_rate) interpreted three different ways

-- Query: DeliveryPerformanceOps
-- Description: Operations perspective - Daily logistics tracking for route optimization and warehouse scheduling
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

-- Query: DeliveryPerformanceSupplier
-- Description: Supplier perspective - Vendor scorecard metrics for evaluation and contract negotiations
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

-- Query: DeliveryPerformanceFinance
-- Description: Finance perspective - Late delivery penalties and cost impact for P&L reporting
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
