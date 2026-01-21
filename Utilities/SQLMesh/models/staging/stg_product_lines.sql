MODEL (
  name staging.stg_product_lines,
  kind SEED (
    path '$root/seeds/product_lines.csv'
  ),
  grain (product_line_id),
  audits (
    UNIQUE_VALUES(columns = (product_line_id)),
    NOT_NULL(columns = (product_line_id))
  )
);
