MODEL (
  name staging.stg_production_schedule,
  kind SEED (
    path '$root/seeds/production_schedule.csv'
  ),
  columns (
    schedule_id TEXT,
    line_id TEXT,
    product_id TEXT,
    scheduled_date DATE,
    shift TEXT,
    planned_quantity INTEGER,
    actual_quantity INTEGER,
    completion_rate DOUBLE,
    status TEXT,
    created_date TIMESTAMP
  ),
  grain (schedule_id),
  audits (
    UNIQUE_VALUES(columns = (schedule_id)),
    NOT_NULL(columns = (schedule_id))
  )
);
