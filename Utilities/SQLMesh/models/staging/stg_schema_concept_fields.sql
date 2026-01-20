MODEL (
  name staging.stg_schema_concept_fields,
  kind FULL,
  grain (id, concept_id),
  audits (
    UNIQUE_VALUES(columns = (concept_id)),
    NOT_NULL(columns = (concept_id))
  ),
);

SELECT
  id,
  table_name,
  field_name,
  concept_id,
  is_primary_meaning,
  context_hint,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.schema_concept_fields;
