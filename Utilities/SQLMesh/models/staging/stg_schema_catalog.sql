MODEL (
  name staging.stg_schema_catalog,
  kind FULL,
  cron '@daily',
  grain (table_name, column_name, data_type)
);

SELECT
  table_name,
  column_name,
  data_type,
  is_nullable::BOOLEAN AS is_nullable,
  is_primary_key::BOOLEAN AS is_primary_key,
  COALESCE(is_shadow_key::BOOLEAN, FALSE) AS is_shadow_key,
  semantic_concept
FROM raw.schema_catalog