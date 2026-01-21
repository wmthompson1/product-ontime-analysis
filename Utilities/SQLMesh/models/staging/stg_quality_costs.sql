MODEL (
  name staging.stg_quality_costs,
  kind SEED (
    path '$root/seeds/quality_costs.csv'
  ),
  columns (
    cost_id TEXT,
    cost_category TEXT,
    cost_period DATE,
    amount DOUBLE,
    budget DOUBLE,
    variance_pct DOUBLE,
    created_date TIMESTAMP
  ),
  grain (cost_id),
  audits (
    UNIQUE_VALUES(columns = (cost_id)),
    NOT_NULL(columns = (cost_id))
  )
);
