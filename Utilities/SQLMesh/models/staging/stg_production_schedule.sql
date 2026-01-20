MODEL (
  name staging.stg_production_schedule,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column planned_start
  ),
  cron '@daily',
  grain (schedule_id, line_id),
  audits (
    UNIQUE_VALUES(columns = (schedule_id)),
    NOT_NULL(columns = (schedule_id))
  )
);

SELECT
  schedule_id,
  line_id,
  product_line,
  planned_start,
  planned_end,
  actual_start,
  actual_end,
  target_quantity,
  actual_quantity,
  efficiency_score,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.production_schedule
WHERE planned_start BETWEEN @start_ds AND @end_ds;
