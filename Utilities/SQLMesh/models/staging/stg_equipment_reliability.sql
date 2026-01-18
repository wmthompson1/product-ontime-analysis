MODEL (
  name staging.stg_equipment_reliability,
  kind SEED (
    path '$root/seeds/equipment_reliability.csv'
  ),
  grain (reliability_id),
  audits (
    UNIQUE_VALUES(columns = (reliability_id)),
    NOT_NULL(columns = (reliability_id))
  )
);
