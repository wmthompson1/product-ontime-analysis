MODEL (
  name staging.stg_industry_benchmarks,
  kind FULL,
  grain (benchmark_id),
  audits (
    UNIQUE_VALUES(columns = (benchmark_id)),
    NOT_NULL(columns = (benchmark_id))
  ),
);

SELECT
  benchmark_id,
  metric_name,
  industry_sector,
  benchmark_value,
  measurement_unit,
  benchmark_class,
  last_updated,
  source,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.industry_benchmarks;
