-- Equipment State: Production View
-- Lists each active shop resource alongside its currently open (non-closed)
-- work order operations, scheduled start/finish windows, and estimated cost.
-- Used by production supervisors to see machine loading and prioritize
-- scheduling decisions.
SELECT
    sr.resource_id,
    sr.description,
    sr.resource_type,
    op.wo_id,
    wo.part_description,
    wo.quantity,
    op.sequence_no,
    op.status                                              AS op_status,
    op.run_hrs                                             AS est_run_hrs,
    op.act_run_hrs                                         AS actual_run_hrs,
    op.sched_start_date,
    op.sched_finish_date,
    ROUND(op.est_atl_lab_cost + op.est_atl_bur_cost, 2)   AS est_total_cost
FROM shop_resource sr
JOIN operation op  ON op.resource_id = sr.resource_id
JOIN work_order wo ON wo.wo_id = op.wo_id
WHERE sr.active = 1
  AND op.status NOT IN ('C', 'Closed')
ORDER BY sr.resource_id, op.sched_start_date
