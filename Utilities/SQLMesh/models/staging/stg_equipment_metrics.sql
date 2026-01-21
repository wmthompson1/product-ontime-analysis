MODEL (
  name staging.stg_equipment_metrics,
  kind SEED (
    path '$root/seeds/equipment_metrics.csv'
  ),
  grain (equipment_id),
  audits (
    NOT_NULL(columns = (equipment_id))
  )
);
