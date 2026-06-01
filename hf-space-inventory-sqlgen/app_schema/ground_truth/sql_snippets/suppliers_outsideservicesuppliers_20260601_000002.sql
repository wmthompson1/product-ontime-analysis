-- Outside Service Suppliers
-- Lists suppliers that perform outside processing (heat treat, NDT,
-- anodize, plating, painting) — used for outside-service PO routing.
SELECT
    s.supplier_id,
    s.supplier_name,
    s.certification_level,
    s.payment_terms,
    s.lead_time_days
FROM suppliers s
WHERE s.outside_service = 1
  AND s.active = 1
ORDER BY s.supplier_name
