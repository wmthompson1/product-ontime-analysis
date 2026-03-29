MODEL (
  name staging.stg_schema_concept_fields,
  kind FULL,
  grain (id, concept_id),
  audits (
    NOT_NULL(columns = (
      concept_id
    ))
  )
);

SELECT
  id,
  NULL AS table_name,
  field_name,
  concept_id,
  NULL AS is_primary_meaning,
  NULL AS context_hint,
  COALESCE(
    CASE WHEN created_at LIKE '____-%' THEN created_at::TIMESTAMP ELSE NULL END,
    CURRENT_TIMESTAMP
  ) AS created_at
FROM raw.schema_concept_fields