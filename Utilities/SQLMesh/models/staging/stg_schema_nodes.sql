MODEL (
  name staging.stg_schema_nodes,
  kind FULL
);

SELECT
  -- map available seed fields conservatively
  node_id AS table_name,
  NULL AS table_type,
  label AS description,
  COALESCE(
    CASE WHEN created_at LIKE '____-%' THEN CAST(created_at AS TIMESTAMP) ELSE NULL END,
    CURRENT_TIMESTAMP
  ) AS created_at
FROM raw.schema_nodes;
