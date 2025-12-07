-- Validation Query 02: Supplier Exposure Analysis
-- Purpose: Assess supply chain risk by analyzing dependency on individual suppliers
-- Identifies single points of failure and calculates supplier performance metrics

-- Main supplier exposure analysis
SELECT 
    s.supplier_code,
    s.supplier_name,
    s.country,
    COUNT(DISTINCT pt.part_id) as parts_supplied,
    COUNT(DISTINCT a.product_id) as products_affected,
    SUM(a.quantity_required) as total_parts_in_bom,
    ROUND(
        100.0 * COUNT(DISTINCT pt.part_id) / 
        (SELECT COUNT(*) FROM parts),
        2
    ) as pct_of_total_parts,
    -- Delivery performance
    COUNT(DISTINCT d.delivery_id) as total_deliveries,
    ROUND(
        100.0 * SUM(CASE WHEN d.is_on_time THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(d.delivery_id), 0),
        2
    ) as on_time_delivery_pct,
    ROUND(AVG(d.days_late), 1) as avg_days_late,
    -- Cost exposure
    ROUND(SUM(pt.unit_cost * a.quantity_required), 2) as total_bom_cost_exposure
FROM suppliers s
LEFT JOIN parts pt ON s.supplier_id = pt.supplier_id
LEFT JOIN assemblies a ON pt.part_id = a.part_id
LEFT JOIN deliveries d ON pt.part_id = d.part_id
GROUP BY s.supplier_id, s.supplier_code, s.supplier_name, s.country
ORDER BY products_affected DESC, total_bom_cost_exposure DESC;

-- Critical supplier risk: Suppliers that affect multiple products with poor delivery
SELECT 
    s.supplier_name,
    s.supplier_code,
    COUNT(DISTINCT a.product_id) as products_at_risk,
    ROUND(
        100.0 * SUM(CASE WHEN d.is_on_time THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(d.delivery_id), 0),
        2
    ) as on_time_delivery_pct,
    'High Risk: Multiple products, poor delivery' as risk_level
FROM suppliers s
JOIN parts pt ON s.supplier_id = pt.supplier_id
JOIN assemblies a ON pt.part_id = a.part_id
LEFT JOIN deliveries d ON pt.part_id = d.part_id
GROUP BY s.supplier_id, s.supplier_name, s.supplier_code
HAVING COUNT(DISTINCT a.product_id) >= 2
    AND (
        100.0 * SUM(CASE WHEN d.is_on_time THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(d.delivery_id), 0)
    ) < 80
ORDER BY products_at_risk DESC;

-- Single-source dependencies: Parts with only one supplier
SELECT 
    pt.part_number,
    pt.part_name,
    s.supplier_name,
    COUNT(DISTINCT a.product_id) as products_affected,
    'Single source - no backup supplier' as risk_note
FROM parts pt
JOIN suppliers s ON pt.supplier_id = s.supplier_id
JOIN assemblies a ON pt.part_id = a.part_id
WHERE pt.part_id IN (
    SELECT part_id 
    FROM parts 
    GROUP BY part_id 
    HAVING COUNT(DISTINCT supplier_id) = 1
)
GROUP BY pt.part_id, pt.part_number, pt.part_name, s.supplier_name
ORDER BY products_affected DESC;
