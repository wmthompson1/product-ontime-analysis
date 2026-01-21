MODEL (
  name staging.stg_production_lines,
  kind SEED (
    path '$root/seeds/production_lines.csv'
  ),
  grain (line_id),
  audits (
    UNIQUE_VALUES(columns = (line_id)),
    NOT_NULL(columns = (line_id))
  )
);
