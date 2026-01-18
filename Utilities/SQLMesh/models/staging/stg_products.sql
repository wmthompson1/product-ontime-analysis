MODEL (
  name staging.stg_products,
  kind SEED (
    path '$root/seeds/products.csv'
  ),
  grain (product_id),
  audits (
    UNIQUE_VALUES(columns = (product_id)),
    NOT_NULL(columns = (product_id))
  )
);
