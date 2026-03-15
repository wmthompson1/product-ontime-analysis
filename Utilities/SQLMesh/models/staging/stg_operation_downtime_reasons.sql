MODEL (
  name staging.stg_operation_downtime_reasons,
  kind FULL,
  cron '@daily',
  columns (
    reason_code TEXT,
    category    TEXT,
    description TEXT
  ),
  grain (reason_code),
  audits (
    UNIQUE_VALUES(columns = (reason_code)),
    NOT_NULL(columns = (reason_code))
  )
);

SELECT
  CAST(ReasonCode  AS TEXT) AS reason_code,
  CAST(Category    AS TEXT) AS category,
  CAST(Description AS TEXT) AS description
FROM raw.operation_downtime_reasons;
