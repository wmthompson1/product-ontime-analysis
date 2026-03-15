MODEL (
  name staging.stg_operation_work_centers,
  kind FULL,
  cron '@daily',
  columns (
    work_center_id   TEXT,
    work_center_name TEXT,
    department_id    TEXT,
    capacity         DOUBLE,
    is_active        INTEGER
  ),
  grain (work_center_id),
  audits (
    UNIQUE_VALUES(columns = (work_center_id)),
    NOT_NULL(columns = (work_center_id))
  )
);

SELECT
  CAST(WorkCenterID   AS TEXT)    AS work_center_id,
  CAST(WorkCenterName AS TEXT)    AS work_center_name,
  CAST(DepartmentID   AS TEXT)    AS department_id,
  CAST(Capacity       AS DOUBLE)  AS capacity,
  CAST(IsActive       AS INTEGER) AS is_active
FROM raw.operation_work_centers;
