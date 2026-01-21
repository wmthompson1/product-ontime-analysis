MODEL (
  name staging.stg_equipment_reliability,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column measurement_period
  ),
  cron '@daily',
  grain (reliability_id, equipment_id),
    partitioned_by (measurement_period),
  audits (
    UNIQUE_VALUES(columns = (reliability_id)),
    NOT_NULL(columns = (reliability_id))
  ),
  
);

SELECT
  reliability_id,
  equipment_id,
  measurement_period,
  mtbf_hours,
  target_mtbf,
  failure_count,
  operating_hours,
  reliability_score,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.equipment_reliability
WHERE measurement_period BETWEEN @start_ds AND @end_ds;
