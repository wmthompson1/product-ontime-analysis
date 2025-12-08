-- Ground Truth SQL: Quality Control Queries
-- Source: Flask Manufacturing App (LangChain Semantic Layer)
-- Category: Quality Control Analytics

-- Query: Daily Defect Rate by Product Line
-- Description: Calculate defect rate percentage for each product line by date
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

-- Query: Non-Conformant Materials Summary
-- Description: Track NCM status and corrective action progress
SELECT 
    n.ncm_id,
    n.material_type,
    n.detection_date,
    n.disposition_status,
    n.quantity_affected,
    c.action_description,
    c.effectiveness_score,
    c.status AS capa_status
FROM non_conformant_materials n
LEFT JOIN corrective_actions c ON n.ncm_id = c.ncm_id
ORDER BY n.detection_date DESC;

-- Query: Quality Incidents by Severity
-- Description: Aggregate quality incidents by severity level
SELECT 
    severity_level,
    COUNT(*) AS incident_count,
    AVG(resolution_time_hours) AS avg_resolution_hours,
    SUM(cost_impact) AS total_cost_impact
FROM quality_incidents
WHERE incident_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY severity_level
ORDER BY incident_count DESC;
