MODEL (
  name staging.stg_failure_events,
  kind SEED (
    path '$root/seeds/failure_events.csv'
  ),
  columns (
    failure_id TEXT,
    equipment_id TEXT,
    failure_date DATE,
    failure_type TEXT,
    failure_mode TEXT,
    severity_level TEXT,
    downtime_hours DOUBLE,
    repair_cost DOUBLE,
    parts_replaced TEXT,
    technician_assigned TEXT,
    failure_description TEXT,
    root_cause_analysis TEXT,
    preventive_action TEXT,
    mtbf_impact DOUBLE,
    created_at TIMESTAMP
  ),
  grain (failure_id),
  audits (
    UNIQUE_VALUES(columns = (failure_id)),
    NOT_NULL(columns = (failure_id))
  )
);
