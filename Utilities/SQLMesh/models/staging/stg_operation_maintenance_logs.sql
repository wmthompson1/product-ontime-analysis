MODEL (
  name staging.stg_operation_maintenance_logs,
  kind FULL,
  cron '@daily',
  columns (
    log_id           TEXT,
    work_center_id   TEXT,
    maintenance_date DATE,
    technician_id    TEXT,
    notes            TEXT
  ),
  grain (log_id),
  audits (
    UNIQUE_VALUES(columns = (log_id)),
    NOT_NULL(columns = (log_id))
  )
);

SELECT
  CAST(LogID            AS TEXT) AS log_id,
  CAST(WorkCenterID     AS TEXT) AS work_center_id,
  CAST(MaintenanceDate  AS DATE) AS maintenance_date,
  CAST(TechnicianID     AS TEXT) AS technician_id,
  CAST(Notes            AS TEXT) AS notes
FROM raw.operation_maintenance_logs;
