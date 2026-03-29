MODEL (
  name staging.stg_product_defects,
  kind SEED (
    path '$root/seeds/product_defects.csv'
  ),
  columns (
    defect_id TEXT,
    product_line TEXT,
    production_date DATE,
    defect_type TEXT,
    defect_count INT,
    total_produced INT,
    defect_rate DOUBLE,
    severity TEXT,
    root_cause TEXT,
    created_date TIMESTAMP
  ),
  grain (
    defect_id
  ),
  audits (UNIQUE_VALUES(columns = (
      defect_id
    )), NOT_NULL(columns = (
      defect_id
  )))
)