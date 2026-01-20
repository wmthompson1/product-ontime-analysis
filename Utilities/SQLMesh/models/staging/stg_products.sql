MODEL (
  name staging.stg_products,
  kind FULL
);

SELECT
  id,
  description
FROM raw.products;
