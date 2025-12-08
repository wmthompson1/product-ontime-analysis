-- Ground Truth SQL: Production Analytics Queries
-- Source: Flask Manufacturing App (LangChain Semantic Layer)
-- Category: Production Performance

-- Query: Production Schedule Adherence
-- Description: Compare planned vs actual production
SELECT 
    line_id,
    product_line,
    planned_start,
    actual_start,
    target_quantity,
    actual_quantity,
    ROUND((actual_quantity::numeric / NULLIF(target_quantity, 0)) * 100, 1) AS completion_pct,
    efficiency_score
FROM production_schedule
WHERE planned_start >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY planned_start DESC;

-- Query: Production Line Performance
-- Description: Aggregate production metrics by line
SELECT 
    pl.line_name,
    pl.line_type,
    COUNT(ps.schedule_id) AS scheduled_runs,
    SUM(ps.target_quantity) AS total_target,
    SUM(ps.actual_quantity) AS total_actual,
    ROUND(AVG(ps.efficiency_score) * 100, 1) AS avg_efficiency_pct
FROM production_lines pl
LEFT JOIN production_schedule ps ON pl.line_id = ps.line_id
WHERE ps.planned_start >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY pl.line_id, pl.line_name, pl.line_type
ORDER BY avg_efficiency_pct DESC;

-- Query: Quality Cost Analysis
-- Description: Track quality-related costs by category
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
