MODEL (
  name staging.stg_operation_shifts,
  kind FULL,
  cron '@daily',
  columns (
    shift_id TEXT,
    shift_name TEXT,
    start_time TEXT,
    end_time TEXT
  ),
  grain (
    shift_id
  ),
  audits (UNIQUE_VALUES(columns = (
      shift_id
    )), NOT_NULL(columns = (
      shift_id
  )))
);

SELECT
  ShiftID::TEXT AS shift_id,
  ShiftName::TEXT AS shift_name,
  StartTime::TEXT AS start_time,
  EndTime::TEXT AS end_time
FROM raw.operation_shifts