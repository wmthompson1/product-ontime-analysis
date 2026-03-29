MODEL (
  name staging.stg_schema_concepts,
  kind FULL,
  grain (concept_id, parent_concept_id)
);

SELECT
  concept_id,
  name AS concept_name, /* map seed 'name' to expected 'concept_name' */
  NULL AS concept_type, /* placeholder when seed doesn't include this field */
  description,
  NULL AS domain,
  NULL AS parent_concept_id,
  COALESCE(
    CASE WHEN created_at LIKE '____-%' THEN created_at::TIMESTAMP ELSE NULL END,
    CURRENT_TIMESTAMP
  ) AS created_at
FROM raw.schema_concepts