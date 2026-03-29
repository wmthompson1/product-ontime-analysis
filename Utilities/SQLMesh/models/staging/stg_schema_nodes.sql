MODEL (
  name staging.stg_schema_nodes,
  kind FULL
);

SELECT
  node_id AS table_name, /* map available seed fields conservatively */
  NULL AS table_type,
  label AS description,
  COALESCE(
    CASE WHEN created_at LIKE '____-%' THEN created_at::TIMESTAMP ELSE NULL END,
    CURRENT_TIMESTAMP
  ) AS created_at
FROM raw.schema_nodes