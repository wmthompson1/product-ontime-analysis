MODEL (
  name staging.stg_daily_deliveries,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column delivery_date
  ),
  cron '@daily',
  grain (delivery_id, supplier_id),
    partitioned_by (delivery_date),
  audits (
    UNIQUE_VALUES(columns = (delivery_id)),
    NOT_NULL(columns = (delivery_id))
  ),
  columns (
    delivery_date "partition key",
    ontime_rate "On-time delivery rate (0-1 scale)",
    quality_score "Quality score from supplier evaluation"
  )
);

SELECT
  delivery_id,
  supplier_id,
  delivery_date,
  planned_quantity,
  actual_quantity,
  ontime_rate,
  quality_score,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.daily_deliveries
WHERE delivery_date BETWEEN @start_ds AND @end_ds;
