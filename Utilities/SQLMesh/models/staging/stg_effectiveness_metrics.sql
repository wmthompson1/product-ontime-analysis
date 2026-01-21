MODEL (
  name staging.stg_effectiveness_metrics,
  kind SEED (
    path '$root/seeds/effectiveness_metrics.csv'
  ),
  grain (metric_id),
  audits (
    UNIQUE_VALUES(columns = (metric_id)),
    NOT_NULL(columns = (metric_id))
  )
);
