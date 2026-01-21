MODEL (
  name staging.stg_production_quality,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column production_date
  ),
  cron '@daily',
  grain (quality_id, shift_id),
  partitioned_by (production_date),
  audits (
    UNIQUE_VALUES(columns = (quality_id)),
    NOT_NULL(columns = (quality_id))
  ),
  
);

SELECT
  quality_id,
  product_line,
  production_date,
  defect_rate,
  total_produced,
  defect_count,
  shift_id,
  line_supervisor,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.production_quality
WHERE production_date BETWEEN @start_ds AND @end_ds;
