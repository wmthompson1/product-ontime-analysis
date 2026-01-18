MODEL (
  name staging.stg_product_defects,
  kind SEED (
    path '$root/seeds/product_defects.csv'
  ),
  grain (defect_id),
  audits (
    UNIQUE_VALUES(columns = (defect_id)),
    NOT_NULL(columns = (defect_id))
  )
);
