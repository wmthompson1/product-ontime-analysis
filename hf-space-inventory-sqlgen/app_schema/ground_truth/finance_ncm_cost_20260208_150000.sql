-- Perspective: Finance
-- Concept: DefectSeverityCost
-- Logic Type: DIRECT
-- SME: Seed data for Solder Validation
SELECT
    d.defect_id,
    d.severity_level,
    d.ncm_cost,
    d.cost_category,
    d.repair_cost + d.scrap_cost AS total_cost_impact
FROM defect_records d
WHERE d.ncm_cost > 0
