-- Supplier Scorecard
-- Lists all active suppliers with their category, certification level,
-- lead time, and outside-service flag for procurement and quality review.
SELECT
    s.supplier_id,
    s.supplier_name,
    s.category,
    s.certification_level,
    s.payment_terms,
    s.lead_time_days,
    CASE WHEN s.outside_service = 1 THEN 'Yes' ELSE 'No' END AS outside_service,
    s.performance_rating
FROM suppliers s
WHERE s.active = 1
ORDER BY s.category, s.supplier_name
