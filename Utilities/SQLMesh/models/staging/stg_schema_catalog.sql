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
  CAST(is_nullable AS BOOLEAN) AS is_nullable,
  CAST(is_primary_key AS BOOLEAN) AS is_primary_key,
  COALESCE(CAST(is_shadow_key AS BOOLEAN), FALSE) AS is_shadow_key,
  semantic_concept
FROM raw.schema_catalog;
