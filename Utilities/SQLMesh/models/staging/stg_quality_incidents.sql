MODEL (
  name staging.stg_quality_incidents,
  kind SEED (
    path '$root/seeds/quality_incidents.csv'
  ),
  grain (incident_id),
  audits (
    UNIQUE_VALUES(columns = (incident_id)),
    NOT_NULL(columns = (incident_id))
  )
);
