MODEL (
  name staging.stg_production_lines,
  kind SEED (
    path '$root/seeds/production_lines.csv'
  ),
  columns (
    line_id TEXT,
    line_name TEXT,
    facility_location TEXT,
    line_type TEXT,
    theoretical_capacity INTEGER,
    actual_capacity INTEGER,
    efficiency_rating DOUBLE,
    installation_date DATE,
    last_maintenance_date DATE,
    status TEXT,
    supervisor TEXT,
    shift_pattern TEXT,
    created_at TIMESTAMP
  ),
  grain (line_id),
  audits (
    UNIQUE_VALUES(columns = (line_id)),
    NOT_NULL(columns = (line_id))
  )
);
