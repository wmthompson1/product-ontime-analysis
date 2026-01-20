MODEL (
  name staging.stg_maintenance_targets,
  kind FULL,
  grain (target_id),
  audits (
    UNIQUE_VALUES(columns = (target_id)),
    NOT_NULL(columns = (target_id))
  ),
);

SELECT
  target_id,
  equipment_type,
  target_mtbf,
  target_availability,
  target_reliability,
  maintenance_interval_hours,
  industry_sector,
  target_class,
  COALESCE(last_updated, CURRENT_DATE) AS last_updated,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.maintenance_targets;
