MODEL (
  name staging.stg_product_defects,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column production_date
  ),
  cron '@daily',
  grain defect_id,
  audits (
    UNIQUE_VALUES(columns = (defect_id)),
    NOT_NULL(columns = (defect_id))
  ),
  columns (
    defect_rate 'Defect rate as percentage',
    severity 'Severity classification (Critical/Major/Minor)'
  )
);

SELECT
  defect_id,
  product_line,
  production_date,
  defect_type,
  defect_count,
  total_produced,
  defect_rate,
  severity,
  root_cause,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.product_defects
WHERE production_date BETWEEN @start_ds AND @end_ds;
