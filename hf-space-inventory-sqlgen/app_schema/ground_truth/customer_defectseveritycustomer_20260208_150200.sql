-- Perspective: Customer
-- Concept: DefectSeverityCustomer
-- Logic Type: DIRECT
-- SME: Seed data for Solder Validation
SELECT
    d.defect_id,
    d.severity_level,
    d.customer_impact_flag,
    d.complaint_id,
    d.customer_notification_date
FROM defect_records d
WHERE d.customer_impact_flag = 1
