-- Equipment State: Compliance View
-- Joins shop resources to receiving inspections and certifications to
-- surface cert-required receipts and their current inspection and cert status.
-- Used by quality and compliance teams to verify that cert-required material
-- processed on each resource has a current, non-expired certificate.
SELECT
    sr.resource_id,
    sr.description,
    sr.resource_type,
    r.receipt_id,
    r.part_id,
    r.inspection_status,
    c.cert_type,
    c.issued_date,
    c.expiry_date,
    c.status                                               AS cert_status
FROM shop_resource sr
JOIN operation op       ON op.resource_id = sr.resource_id
JOIN work_order wo      ON wo.wo_id        = op.wo_id
JOIN receiving r        ON r.part_id       = wo.part_id
LEFT JOIN certification c ON c.receipt_id  = r.receipt_id
WHERE sr.active = 1
  AND r.cert_required = 1
ORDER BY sr.resource_id, r.receipt_date DESC
