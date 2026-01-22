MODEL (
  name staging.stg_schema_nodes,
  kind FULL
);

SELECT
  table_name,
  table_type,
  description,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.schema_nodes;
