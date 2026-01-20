MODEL (
  name staging.stg_quality_incidents,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column incident_date
  ),
  cron '@daily',
  grain (incident_id),
    partitioned_by (incident_date),
  audits (
    UNIQUE_VALUES(columns = (incident_id)),
    NOT_NULL(columns = (incident_id))
  ),
  columns (
    incident_date "partition key",
    severity_level "Severity level for prioritization",
    cost_impact "Financial impact in dollars"
  )
);

SELECT
  incident_id,
  product_line,
  incident_date,
  incident_type,
  severity_level,
  affected_units,
  cost_impact,
  detection_method,
  status,
  assigned_to,
  resolution_date,
  root_cause,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.quality_incidents
WHERE incident_date BETWEEN @start_ds AND @end_ds;
