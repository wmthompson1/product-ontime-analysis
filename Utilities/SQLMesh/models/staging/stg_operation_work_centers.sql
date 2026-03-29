MODEL (
  name staging.stg_operation_work_centers,
  kind FULL,
  cron '@daily',
  columns (
    work_center_id TEXT,
    work_center_name TEXT,
    department_id TEXT,
    capacity DOUBLE,
    is_active INT
  ),
  grain (
    work_center_id
  ),
  audits (
    UNIQUE_VALUES(columns = (
      work_center_id
    )),
    NOT_NULL(columns = (
      work_center_id
    ))
  )
);

SELECT
  WorkCenterID::TEXT AS work_center_id,
  WorkCenterName::TEXT AS work_center_name,
  DepartmentID::TEXT AS department_id,
  Capacity::DOUBLE AS capacity,
  IsActive::INT AS is_active
FROM raw.operation_work_centers