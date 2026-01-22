MODEL (
  name staging.stg_manufacturing_acronyms,
  kind FULL,
  grain acronym_id,
  audits (
    UNIQUE_VALUES(columns = (acronym_id)),
    NOT_NULL(columns = (acronym_id))
  )
);

SELECT
  acronym_id,
  acronym,
  definition,
  table_name,
  category,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at,
  COALESCE(updated_at, CURRENT_TIMESTAMP) AS updated_at
FROM raw.manufacturing_acronyms;
