MODEL (
  name staging.stg_production_quality,
  kind SEED (
    path '$root/seeds/production_quality.csv'
  ),
  columns (
    quality_id TEXT,
    line_id TEXT,
    measurement_date DATE,
    total_produced INT,
    passed_inspection INT,
    failed_inspection INT,
    first_pass_yield DOUBLE,
    rework_count INT,
    scrap_count INT,
    created_date TIMESTAMP
  ),
  grain (
    quality_id
  ),
  audits (UNIQUE_VALUES(columns = (
      quality_id
    )), NOT_NULL(columns = (
      quality_id
  )))
)