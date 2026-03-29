MODEL (
  name staging.stg_operation_labor_codes,
  kind FULL,
  cron '@daily',
  columns (
    labor_code TEXT,
    description TEXT,
    hourly_rate DOUBLE
  ),
  grain (
    labor_code
  ),
  audits (UNIQUE_VALUES(columns = (
      labor_code
    )), NOT_NULL(columns = (
      labor_code
  )))
);

SELECT
  LaborCode::TEXT AS labor_code,
  Description::TEXT AS description,
  HourlyRate::DOUBLE AS hourly_rate
FROM raw.operation_labor_codes