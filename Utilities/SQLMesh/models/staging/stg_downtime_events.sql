MODEL (
  name staging.stg_downtime_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_start_time
  ),
  cron '@daily',
  grain (event_id, line_id, equipment_id),
    partitioned_by (event_start_time),
  audits (
    UNIQUE_VALUES(columns = (event_id)),
    NOT_NULL(columns = (event_id))
  ),
  columns (
    event_start_time "partition key",
    cost_impact "Financial impact in dollars"
  )
);

SELECT
  event_id,
  line_id,
  equipment_id,
  event_start_time,
  event_end_time,
  downtime_duration_minutes,
  downtime_category,
  downtime_reason,
  impact_severity,
  production_loss_units,
  cost_impact,
  resolution_method,
  reported_by,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.downtime_events
WHERE event_start_time BETWEEN @start_ds AND @end_ds;
