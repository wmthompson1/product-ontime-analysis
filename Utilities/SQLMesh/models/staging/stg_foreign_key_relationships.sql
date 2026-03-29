MODEL (
  name staging.stg_foreign_key_relationships,
  kind FULL,
  cron '@daily',
  grain (from_table, from_column, to_table, to_column)
);

SELECT
  from_table,
  from_column,
  to_table,
  to_column,
  fk_type,
  perspective
FROM raw.foreign_key_relationships