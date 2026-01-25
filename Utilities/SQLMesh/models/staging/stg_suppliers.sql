MODEL (
  name staging.stg_suppliers,
  kind SEED (
    path '$root/seeds/suppliers.csv'
  ),
  columns (
    supplier_id TEXT,
    supplier_name TEXT,
    contact_email TEXT,
    phone TEXT,
    address TEXT,
    performance_rating DOUBLE,
    certification_level TEXT,
    lead_time_days INTEGER,
    payment_terms TEXT,
    created_date TIMESTAMP
  ),
  grain (supplier_id),
  audits (
    UNIQUE_VALUES(columns = (supplier_id)),
    NOT_NULL(columns = (supplier_id))
  )
);
