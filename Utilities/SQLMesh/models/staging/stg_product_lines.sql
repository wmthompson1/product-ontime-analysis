MODEL (
  name staging.stg_product_lines,
  kind FULL,
  grain (product_line_id),
  audits (
    UNIQUE_VALUES(columns = (product_line_id)),
    NOT_NULL(columns = (product_line_id))
  ),
);

SELECT
  product_line_id,
  product_line_name,
  product_category,
  target_volume,
  unit_price,
  profit_margin,
  launch_date,
  lifecycle_stage,
  primary_market,
  complexity_rating,
  regulatory_requirements,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.product_lines;
