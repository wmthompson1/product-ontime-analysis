-- Validation Query 01: Assemblies Part Counts
-- Purpose: Verify bill of materials integrity and calculate total parts per product
-- This query helps identify products with complex assemblies and potential supply chain exposure

SELECT 
    p.product_code,
    p.product_name,
    p.product_family,
    COUNT(DISTINCT a.part_id) as unique_parts_count,
    SUM(a.quantity_required) as total_parts_required,
    COUNT(DISTINCT pt.supplier_id) as unique_suppliers,
    ROUND(AVG(pt.unit_cost * a.quantity_required), 2) as avg_component_cost,
    STRING_AGG(DISTINCT s.supplier_name, ', ' ORDER BY s.supplier_name) as supplier_names
FROM products p
LEFT JOIN assemblies a ON p.product_id = a.product_id
LEFT JOIN parts pt ON a.part_id = pt.part_id
LEFT JOIN suppliers s ON pt.supplier_id = s.supplier_id
GROUP BY p.product_id, p.product_code, p.product_name, p.product_family
ORDER BY unique_parts_count DESC, total_parts_required DESC;

-- Additional validation: Check for products without any parts defined
SELECT 
    p.product_code,
    p.product_name,
    'No parts defined in BOM' as validation_issue
FROM products p
LEFT JOIN assemblies a ON p.product_id = a.product_id
WHERE a.assembly_id IS NULL;

-- Additional validation: Parts without supplier assignments
SELECT 
    pt.part_number,
    pt.part_name,
    'No supplier assigned' as validation_issue
FROM parts pt
WHERE pt.supplier_id IS NULL;
