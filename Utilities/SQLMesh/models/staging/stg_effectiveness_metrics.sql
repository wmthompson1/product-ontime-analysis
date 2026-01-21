MODEL (
  name staging.stg_effectiveness_metrics,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column measurement_date
  ),
  cron '@daily',
  grain (metric_id),
    partitioned_by (measurement_date),
  audits (
    UNIQUE_VALUES(columns = (metric_id)),
    NOT_NULL(columns = (metric_id))
  ),
);

SELECT
  metric_id,
  measurement_date,
  metric_type,
  metric_value,
  target_value,
  variance_percentage,
  measurement_unit,
  department,
  measurement_method,
  confidence_level,
  data_source,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.effectiveness_metrics
WHERE measurement_date BETWEEN @start_ds AND @end_ds;
