MODEL (
  name staging.stg_production_quality,
  kind SEED (
    path '$root/seeds/production_quality.csv'
  ),
  grain (quality_id),
  audits (
    UNIQUE_VALUES(columns = (quality_id)),
    NOT_NULL(columns = (quality_id))
  )
);
