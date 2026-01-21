MODEL (
  name staging.stg_failure_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column failure_date
  ),
  cron '@daily',
  grain (failure_id, equipment_id),
    partitioned_by (failure_date),
  audits (
    UNIQUE_VALUES(columns = (failure_id)),
    NOT_NULL(columns = (failure_id))
  ),
  columns (
    failure_date timestamp "partition key",
    severity_level varchar "Severity level for prioritization",
    downtime_hours double "Downtime duration in hours"
  )
);

SELECT
  failure_id,
  equipment_id,
  failure_date,
  failure_type,
  failure_mode,
  severity_level,
  downtime_hours,
  repair_cost,
  parts_replaced,
  technician_assigned,
  failure_description,
  root_cause_analysis,
  preventive_action,
  mtbf_impact,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.failure_events
WHERE failure_date BETWEEN @start_ds AND @end_ds;
