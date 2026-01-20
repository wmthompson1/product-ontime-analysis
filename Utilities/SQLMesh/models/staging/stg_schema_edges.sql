MODEL (
  name staging.stg_schema_edges,
  kind FULL,
  grain (edge_id),
  audits (
    UNIQUE_VALUES(columns = (edge_id)),
    NOT_NULL(columns = (edge_id))
  ),
);

SELECT
  edge_id,
  from_table,
  to_table,
  relationship_type,
  join_column,
  weight,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at,
  join_column_description,
  natural_language_alias,
  few_shot_example,
  context
FROM raw.schema_edges;
