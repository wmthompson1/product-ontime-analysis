MODEL (
  name staging.stg_operation_downtime_reasons,
  kind FULL,
  cron '@daily',
  columns (
    reason_code TEXT,
    category TEXT,
    description TEXT
  ),
  grain (
    reason_code
  ),
  audits (
    UNIQUE_VALUES(columns = (
      reason_code
    )),
    NOT_NULL(columns = (
      reason_code
    ))
  )
);

SELECT
  ReasonCode::TEXT AS reason_code,
  Category::TEXT AS category,
  Description::TEXT AS description
FROM raw.operation_downtime_reasons