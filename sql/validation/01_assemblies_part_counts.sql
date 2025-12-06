-- Validation 01: list assemblies and their total part counts
SELECT a.assembly_id, a.assembly_code, COUNT(ap.part_id) AS distinct_parts, SUM(ap.qty) AS total_parts
FROM pta.assemblies a
LEFT JOIN pta.assembly_parts ap ON a.assembly_id = ap.assembly_id
GROUP BY a.assembly_id, a.assembly_code
ORDER BY a.assembly_id;
