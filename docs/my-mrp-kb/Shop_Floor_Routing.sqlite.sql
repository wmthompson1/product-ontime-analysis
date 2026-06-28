/*
Shop Floor Work & Routing — SQLite grounding query (SYNTHETIC).

This is the runnable SQLite query that grounds the companion document
"Shop Floor Work and Routing - Aerospace MRP.md". It is a strict TWO-TABLE
join of work_order and operation in the local synthetic manufacturing.db.
operation.resource_id is treated as the WORK STATION (the place the routing
step runs). No third table is joined — a human-readable work-station name from
shop_resource is mentioned in the prose only, never added as a join here.

Per project convention the synthetic target dialect is SQLite (manufacturing.db).
The real Infor VISUAL T-SQL (Live.dbo.WORK_ORDER / Live.dbo.OPERATION) is a
faithful reference benchmark only — not the synthetic target.

Ground-truth (Live.dbo.*, T-SQL)   ->  stand-in (manufacturing.db, SQLite)
  WORK_ORDER                        ->  work_order
  OPERATION                         ->  operation
  OPERATION.RESOURCE_ID             ->  operation.resource_id  (the work station)
  WORK_ORDER.BASE_ID / LOT_ID / …   ->  work_order.wo_id       (single surrogate key)
  OPERATION.OPERATION_SEQ_NO        ->  operation.sequence_no  (gapped: 20, 80, 220…)
  setup/run + actuals (hours)       ->  setup_hrs / run_hrs / act_setup_hrs / act_run_hrs

Join key: operation.wo_id = work_order.wo_id.

----------------------------------------------------------------------
QUERY 1 — Detailed routing for ONE work order (the routing "traveler").
Shows every routed step in sequence, which work station runs it, the kind of
operation, the step status (Q=Queued, S=Started, C=Complete), scheduled vs.
actual hours, and scheduled vs. actual cost (labor + burden + outside-service).
WO-240003 is a closed AIRFRAME job that has real actual hours and cost, so the
scheduled-vs-actual columns are meaningful. Swap the literal to inspect any
other work order (e.g. 'WO-240005' for a job still in process).
----------------------------------------------------------------------
*/

SELECT
    wo.wo_id,
    wo.routing_template,
    wo.status                              AS wo_status,
    op.sequence_no,
    op.resource_id                         AS work_station,
    op.operation_type_id                   AS op_type,
    op.status                              AS op_status,
    ROUND(op.setup_hrs + op.run_hrs, 2)        AS sched_hrs,
    ROUND(op.act_setup_hrs + op.act_run_hrs, 2) AS act_hrs,
    ROUND((op.act_setup_hrs + op.act_run_hrs)
          - (op.setup_hrs + op.run_hrs), 2)     AS hrs_variance,
    ROUND(op.est_atl_lab_cost + op.est_atl_bur_cost + op.est_atl_ser_cost, 2) AS sched_cost,
    ROUND(op.act_atl_lab_cost + op.act_atl_bur_cost + op.act_atl_ser_cost, 2) AS act_cost
FROM work_order wo
JOIN operation op
    ON op.wo_id = wo.wo_id
WHERE wo.wo_id = 'WO-240003'
ORDER BY op.sequence_no;

/*
----------------------------------------------------------------------
QUERY 2 — Work-station load & scheduled-vs-actual hours (the shop view).
Still a strict two-table join. Rolls every routed operation up to its work
station (resource_id) across all work orders, so you can see which stations
carry the most steps and how their actual hours compare to plan. A negative
variance means the floor beat the estimate; a positive variance means it
overran. Outside-service stations (OUTSIDE, SV-*) usually show scheduled = 0
because the time is bought from a vendor, not run in-house.
----------------------------------------------------------------------
*/

SELECT
    op.resource_id                              AS work_station,
    COUNT(*)                                    AS routed_ops,
    SUM(CASE WHEN op.status = 'C' THEN 1 ELSE 0 END) AS completed_ops,
    SUM(CASE WHEN op.status = 'S' THEN 1 ELSE 0 END) AS started_ops,
    SUM(CASE WHEN op.status = 'Q' THEN 1 ELSE 0 END) AS queued_ops,
    ROUND(SUM(op.setup_hrs + op.run_hrs), 1)        AS sched_hrs,
    ROUND(SUM(op.act_setup_hrs + op.act_run_hrs), 1) AS act_hrs
FROM work_order wo
JOIN operation op
    ON op.wo_id = wo.wo_id
GROUP BY op.resource_id
ORDER BY routed_ops DESC, work_station;
