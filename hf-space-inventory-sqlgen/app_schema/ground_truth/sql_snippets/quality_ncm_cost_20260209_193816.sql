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
ORDER BY n.detection_date DESC;SELECT