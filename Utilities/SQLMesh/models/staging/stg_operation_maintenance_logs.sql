MODEL (
  name staging.stg_operation_maintenance_logs,
  kind FULL,
  cron '@daily',
  columns (
    log_id TEXT,
    work_center_id TEXT,
    maintenance_date DATE,
    technician_id TEXT,
    notes TEXT
  ),
  grain (
    log_id
  ),
  audits (UNIQUE_VALUES(columns = (
      log_id
    )), NOT_NULL(columns = (
      log_id
  )))
);

SELECT
  LogID::TEXT AS log_id,
  WorkCenterID::TEXT AS work_center_id,
  MaintenanceDate::DATE AS maintenance_date,
  TechnicianID::TEXT AS technician_id,
  Notes::TEXT AS notes
FROM raw.operation_maintenance_logs