MODEL (
  name staging.stg_operation_labor_codes,
  kind FULL,
  cron '@daily',
  columns (
    labor_code   TEXT,
    description  TEXT,
    hourly_rate  DOUBLE
  ),
  grain (labor_code),
  audits (
    UNIQUE_VALUES(columns = (labor_code)),
    NOT_NULL(columns = (labor_code))
  )
);

SELECT
  CAST(LaborCode   AS TEXT)   AS labor_code,
  CAST(Description AS TEXT)   AS description,
  CAST(HourlyRate  AS DOUBLE) AS hourly_rate
FROM raw.operation_labor_codes;
