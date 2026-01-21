MODEL (
  name staging.stg_daily_deliveries,
  kind SEED (
    path '$root/seeds/daily_deliveries.csv'
  ),
  columns (
    delivery_id TEXT,
    supplier_id TEXT,
    delivery_date DATE,
    planned_quantity INTEGER,
    actual_quantity INTEGER,
    ontime_rate DOUBLE,
    quality_score DOUBLE,
    created_date TIMESTAMP
  ),
  grain (delivery_id),
  audits (
    UNIQUE_VALUES(columns = (delivery_id)),
    NOT_NULL(columns = (delivery_id))
  )
);
