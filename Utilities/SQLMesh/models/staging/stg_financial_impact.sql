MODEL (
  name staging.stg_financial_impact,
  kind SEED (
    path '$root/seeds/financial_impact.csv'
  ),
  grain (impact_id),
  audits (
    UNIQUE_VALUES(columns = (impact_id)),
    NOT_NULL(columns = (impact_id))
  )
);
