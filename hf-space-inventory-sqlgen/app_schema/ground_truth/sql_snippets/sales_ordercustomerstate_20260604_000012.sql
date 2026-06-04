-- Order Customer State: Work Order Delivery Status
-- Summarizes work order status against required delivery dates to provide
-- a customer-facing view of order progress. Classifies each order as
-- On Time, Late, Overdue, At Risk, or On Schedule.
SELECT
    wo.wo_id,
    wo.part_id,
    wo.part_description,
    wo.quantity,
    wo.status,
    wo.open_date,
    wo.required_date,
    wo.close_date,
    CASE
        WHEN wo.close_date IS NOT NULL
             AND wo.close_date <= wo.required_date           THEN 'On Time'
        WHEN wo.close_date IS NOT NULL
             AND wo.close_date >  wo.required_date           THEN 'Late'
        WHEN wo.close_date IS NULL
             AND date('now') > wo.required_date              THEN 'Overdue'
        WHEN wo.close_date IS NULL
             AND date('now') > date(wo.required_date, '-7 days') THEN 'At Risk'
        ELSE 'On Schedule'
    END                                                      AS customer_delivery_status
FROM work_order wo
ORDER BY
    CASE
        WHEN wo.close_date IS NULL
             AND date('now') > wo.required_date              THEN 1
        WHEN wo.close_date IS NULL
             AND date('now') > date(wo.required_date, '-7 days') THEN 2
        WHEN wo.close_date IS NOT NULL
             AND wo.close_date > wo.required_date            THEN 3
        ELSE 4
    END,
    wo.required_date
