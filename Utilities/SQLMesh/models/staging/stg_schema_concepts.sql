MODEL (
  name staging.stg_schema_concepts,
  kind FULL,
  grain (concept_id, parent_concept_id)
);

SELECT
  concept_id,
  concept_name,
  concept_type,
  description,
  domain,
  parent_concept_id,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.schema_concepts;
