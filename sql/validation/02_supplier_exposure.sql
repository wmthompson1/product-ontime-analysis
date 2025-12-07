-- Validation 02: supplier exposure by assembly (sum of unit_cost * qty per assembly per supplier)
SELECT s.supplier_id, s.name AS supplier_name, a.assembly_id, a.assembly_code,
       SUM(p.unit_cost * ap.qty) AS exposure_cost
FROM pta.suppliers s
JOIN pta.parts p ON p.supplier_id = s.supplier_id
JOIN pta.assembly_parts ap ON ap.part_id = p.part_id
JOIN pta.assemblies a ON a.assembly_id = ap.assembly_id
GROUP BY s.supplier_id, s.name, a.assembly_id, a.assembly_code
ORDER BY s.supplier_id, a.assembly_id;
