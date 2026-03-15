MODEL (
  name staging.stg_operation_production_metrics,
  kind FULL,
  cron '@daily',
  columns (
    metric_id     TEXT,
    work_order_id TEXT,
    actual_output DOUBLE,
    scrap_count   INTEGER,
    captured_at   TIMESTAMP
  ),
  grain (metric_id),
  audits (
    UNIQUE_VALUES(columns = (metric_id)),
    NOT_NULL(columns = (metric_id))
  )
);

SELECT
  CAST(MetricID      AS TEXT)      AS metric_id,
  CAST(WorkOrderID   AS TEXT)      AS work_order_id,
  CAST(ActualOutput  AS DOUBLE)    AS actual_output,
  CAST(ScrapCount    AS INTEGER)   AS scrap_count,
  CAST(Timestamp     AS TIMESTAMP) AS captured_at
FROM raw.operation_production_metrics;
