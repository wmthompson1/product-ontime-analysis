-- Work Order Cost Detail
-- Per-work-order cost breakdown (labor, burden, outside service, material).
-- Used for WIP valuation and job costing analysis.
SELECT
    wo.wo_id,
    wo.workorder_type,
    wo.part_id,
    wo.part_description,
    wo.quantity,
    wo.status,
    wo.routing_template,
    ROUND(wo.act_lab_cost, 2)  AS act_labor,
    ROUND(wo.act_bur_cost, 2)  AS act_burden,
    ROUND(wo.act_ser_cost, 2)  AS act_outside_service,
    ROUND(wo.act_mat_cost, 2)  AS act_material,
    ROUND(wo.act_lab_cost + wo.act_bur_cost + wo.act_ser_cost + wo.act_mat_cost, 2) AS total_actual_cost
FROM work_order wo
ORDER BY total_actual_cost DESC
