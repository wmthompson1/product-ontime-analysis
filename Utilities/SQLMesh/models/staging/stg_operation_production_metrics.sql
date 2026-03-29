MODEL (
  name staging.stg_operation_production_metrics,
  kind FULL,
  cron '@daily',
  columns (
    metric_id TEXT,
    work_order_id TEXT,
    actual_output DOUBLE,
    scrap_count INT,
    captured_at TIMESTAMP
  ),
  grain (
    metric_id
  ),
  audits (UNIQUE_VALUES(columns = (
      metric_id
    )), NOT_NULL(columns = (
      metric_id
  )))
);

SELECT
  MetricID::TEXT AS metric_id,
  WorkOrderID::TEXT AS work_order_id,
  ActualOutput::DOUBLE AS actual_output,
  ScrapCount::INT AS scrap_count,
  Timestamp::TIMESTAMP AS captured_at
FROM raw.operation_production_metrics