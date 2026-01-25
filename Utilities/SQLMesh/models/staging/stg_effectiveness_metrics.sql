MODEL (
  name staging.stg_effectiveness_metrics,
  kind SEED (
    path '$root/seeds/effectiveness_metrics.csv'
  ),
  columns (
    metric_id TEXT,
    action_id TEXT,
    metric_type TEXT,
    baseline_value DOUBLE,
    target_value DOUBLE,
    actual_value DOUBLE,
    improvement_pct DOUBLE,
    measurement_date DATE,
    verified_by TEXT,
    created_date TIMESTAMP
  ),
  grain (metric_id),
  audits (
    UNIQUE_VALUES(columns = (metric_id)),
    NOT_NULL(columns = (metric_id))
  )
);
