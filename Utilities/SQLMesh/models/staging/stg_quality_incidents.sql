MODEL (
  name staging.stg_quality_incidents,
  kind SEED (
    path '$root/seeds/quality_incidents.csv'
  ),
  columns (
    incident_id TEXT,
    product_line TEXT,
    incident_date DATE,
    incident_type TEXT,
    severity_level TEXT,
    affected_units INTEGER,
    cost_impact DOUBLE,
    detection_method TEXT,
    status TEXT,
    assigned_to TEXT,
    resolution_date DATE,
    root_cause TEXT,
    created_at TIMESTAMP
  ),
  grain (incident_id),
  audits (
    UNIQUE_VALUES(columns = (incident_id)),
    NOT_NULL(columns = (incident_id))
  )
);
