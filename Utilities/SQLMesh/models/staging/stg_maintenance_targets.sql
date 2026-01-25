MODEL (
  name staging.stg_maintenance_targets,
  kind SEED (
    path '$root/seeds/maintenance_targets.csv'
  ),
  columns (
    target_id TEXT,
    equipment_id TEXT,
    target_year INTEGER,
    target_mtbf DOUBLE,
    target_availability DOUBLE,
    target_oee DOUBLE,
    pm_interval_days INTEGER,
    created_date TIMESTAMP
  ),
  grain (target_id),
  audits (
    UNIQUE_VALUES(columns = (target_id)),
    NOT_NULL(columns = (target_id))
  )
);
