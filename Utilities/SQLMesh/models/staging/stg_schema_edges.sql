MODEL (
  name staging.stg_schema_edges,
  kind FULL,
  grain edge_id,
  audits (
    UNIQUE_VALUES(columns = (edge_id)),
    NOT_NULL(columns = (edge_id))
  )
);

SELECT
  edge_id,
  from_node AS from_table,
  to_node AS to_table,
  relation AS relationship_type,
  NULL AS join_column,
  NULL AS weight,
  COALESCE(
    CASE WHEN created_at LIKE '____-%' THEN CAST(created_at AS TIMESTAMP) ELSE NULL END,
    CURRENT_TIMESTAMP
  ) AS created_at,
  NULL AS join_column_description,
  NULL AS natural_language_alias,
  NULL AS few_shot_example,
  NULL AS context
FROM raw.schema_edges;
