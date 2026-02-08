SELECT 
    cost_category,
    cost_subcategory,
    SUM(cost_amount) AS total_cost,
    SUM(units_affected) AS total_units,
    ROUND(AVG(cost_per_unit), 2) AS avg_cost_per_unit,
    COUNT(*) AS incident_count
FROM quality_costs
WHERE cost_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY cost_category, cost_subcategory
ORDER BY total_cost DESC;
