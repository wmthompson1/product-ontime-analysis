-- Open Work Orders by Status
-- Summary of work orders grouped by status with cost rollup.
-- Used for production planning and WIP visibility.
SELECT
    wo.status,
    COUNT(*)            AS order_count,
    SUM(wo.quantity)    AS total_qty,
    ROUND(SUM(wo.act_lab_cost + wo.act_bur_cost + wo.act_ser_cost + wo.act_mat_cost), 2) AS total_actual_cost,
    SUM(wo.outside_service) AS orders_with_outside_service
FROM work_order wo
GROUP BY wo.status
ORDER BY order_count DESC
