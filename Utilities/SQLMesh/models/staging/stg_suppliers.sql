MODEL (
  name staging.stg_suppliers,
  kind SEED (
    path '$root/seeds/suppliers.csv'
  ),
  grain (supplier_id),
  audits (
    UNIQUE_VALUES(columns = (supplier_id)),
    NOT_NULL(columns = (supplier_id))
  )
);
