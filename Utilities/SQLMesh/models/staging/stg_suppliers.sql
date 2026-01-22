MODEL (
  name staging.stg_suppliers,
  kind FULL,
  grain supplier_id,
  audits (
    UNIQUE_VALUES(columns = (supplier_id)),
    NOT_NULL(columns = (supplier_id))
  )
);

SELECT
  supplier_id,
  supplier_name,
  contact_email,
  phone,
  address,
  performance_rating,
  certification_level,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.suppliers;
