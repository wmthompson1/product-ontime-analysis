MODEL (
  name staging.stg_maintenance_targets,
  kind SEED (
    path '$root/seeds/maintenance_targets.csv'
  ),
  grain (target_id),
  audits (
    UNIQUE_VALUES(columns = (target_id)),
    NOT_NULL(columns = (target_id))
  )
);
