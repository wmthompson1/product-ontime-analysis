SELECT 
    product_line,
    production_date,
    defect_count,
    total_produced,
    ROUND((defect_count::numeric / NULLIF(total_produced, 0)) * 100, 2) AS defect_rate_pct,
    severity,
    root_cause
FROM product_defects
WHERE production_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY production_date DESC, defect_rate_pct DESC;
