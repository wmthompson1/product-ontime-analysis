MODEL (
  name staging.stg_operation_resources,
  kind FULL,
  cron '@daily',
  columns (
    resource_id   TEXT,
    resource_type TEXT,
    status        TEXT
  ),
  grain (resource_id),
  audits (
    UNIQUE_VALUES(columns = (resource_id)),
    NOT_NULL(columns = (resource_id))
  )
);

SELECT
  CAST(ResourceID   AS TEXT) AS resource_id,
  CAST(ResourceType AS TEXT) AS resource_type,
  CAST(Status       AS TEXT) AS status
FROM raw.operation_resources;
