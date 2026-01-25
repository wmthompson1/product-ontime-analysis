MODEL (
  name staging.stg_product_lines,
  kind SEED (
    path '$root/seeds/product_lines.csv'
  ),
  columns (
    product_line_id TEXT,
    product_line_name TEXT,
    product_category TEXT,
    target_volume INTEGER,
    unit_price DOUBLE,
    profit_margin DOUBLE,
    launch_date DATE,
    lifecycle_stage TEXT,
    primary_market TEXT,
    complexity_rating TEXT,
    regulatory_requirements TEXT,
    created_at TIMESTAMP
  ),
  grain (product_line_id),
  audits (
    UNIQUE_VALUES(columns = (product_line_id)),
    NOT_NULL(columns = (product_line_id))
  )
);
