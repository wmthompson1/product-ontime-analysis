MODEL (
  name staging.stg_schema_concept_fields,
  kind FULL,
  grain (id, concept_id),
  audits (
    UNIQUE_VALUES(columns = (concept_id)),
    NOT_NULL(columns = (concept_id))
  )
);

SELECT
  -- map seed 'field_id' to expected 'id'
  field_id AS id,
  NULL AS table_name,
  field_name,
  concept_id,
  NULL AS is_primary_meaning,
  NULL AS context_hint,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.schema_concept_fields;
