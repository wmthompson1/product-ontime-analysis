MODEL (
  name staging.stg_products,
  kind SEED (
    path '$root/seeds/products.csv'
  ),
  columns (
    product_id TEXT,
    product_name TEXT,
    product_category TEXT,
    unit_cost DOUBLE,
    unit_price DOUBLE,
    weight_kg DOUBLE,
    lead_time_days INTEGER,
    min_order_qty INTEGER,
    status TEXT,
    created_date TIMESTAMP
  ),
  grain (product_id),
  audits (
    UNIQUE_VALUES(columns = (product_id)),
    NOT_NULL(columns = (product_id))
  )
);
