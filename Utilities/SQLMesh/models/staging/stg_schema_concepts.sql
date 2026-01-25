MODEL (
  name staging.stg_schema_concepts,
  kind FULL,
  grain (concept_id, parent_concept_id)
);

SELECT
  concept_id,
  -- map seed 'name' to expected 'concept_name'
  name AS concept_name,
  -- placeholder when seed doesn't include this field
  NULL AS concept_type,
  description,
  NULL AS domain,
  NULL AS parent_concept_id,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.schema_concepts;
