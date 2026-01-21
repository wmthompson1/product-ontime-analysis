MODEL (
  name staging.stg_quality_costs,
  kind SEED (
    path '$root/seeds/quality_costs.csv'
  ),
  grain (cost_id),
  audits (
    UNIQUE_VALUES(columns = (cost_id)),
    NOT_NULL(columns = (cost_id))
  )
);
