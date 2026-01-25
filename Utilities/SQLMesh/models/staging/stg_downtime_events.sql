MODEL (
  name staging.stg_downtime_events,
  kind SEED (
    path '$root/seeds/downtime_events.csv'
  ),
  columns (
    event_id TEXT,
    line_id TEXT,
    equipment_id TEXT,
    event_start_time TIMESTAMP,
    event_end_time TIMESTAMP,
    downtime_duration_minutes INTEGER,
    downtime_category TEXT,
    downtime_reason TEXT,
    impact_severity TEXT,
    production_loss_units INTEGER,
    cost_impact DOUBLE,
    resolution_method TEXT,
    reported_by TEXT,
    created_at TIMESTAMP
  ),
  grain (event_id),
  audits (
    UNIQUE_VALUES(columns = (event_id)),
    NOT_NULL(columns = (event_id))
  )
);
