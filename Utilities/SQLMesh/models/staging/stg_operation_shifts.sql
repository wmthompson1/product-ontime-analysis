MODEL (
  name staging.stg_operation_shifts,
  kind FULL,
  cron '@daily',
  columns (
    shift_id   TEXT,
    shift_name TEXT,
    start_time TEXT,
    end_time   TEXT
  ),
  grain (shift_id),
  audits (
    UNIQUE_VALUES(columns = (shift_id)),
    NOT_NULL(columns = (shift_id))
  )
);

SELECT
  CAST(ShiftID    AS TEXT) AS shift_id,
  CAST(ShiftName  AS TEXT) AS shift_name,
  CAST(StartTime  AS TEXT) AS start_time,
  CAST(EndTime    AS TEXT) AS end_time
FROM raw.operation_shifts;
