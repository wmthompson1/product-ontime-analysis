MODEL (
  name staging.stg_equipment_metrics,
  kind SEED (
    path '$root/seeds/equipment_metrics.csv'
  ),
  columns (
    equipment_id TEXT,
    line_id TEXT,
    equipment_type TEXT,
    equipment_name TEXT,
    measurement_date DATE,
    availability_rate DOUBLE,
    performance_rate DOUBLE,
    quality_rate DOUBLE,
    oee_score DOUBLE,
    downtime_hours DOUBLE,
    created_date TIMESTAMP
  ),
  grain (equipment_id),
  audits (
    NOT_NULL(columns = (equipment_id))
  )
);
