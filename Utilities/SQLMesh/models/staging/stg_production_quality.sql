MODEL (
  name staging.stg_production_quality,
  kind SEED (
    path '$root/seeds/production_quality.csv'
  ),
  columns (
    quality_id TEXT,
    line_id TEXT,
    measurement_date DATE,
    total_produced INTEGER,
    passed_inspection INTEGER,
    failed_inspection INTEGER,
    first_pass_yield DOUBLE,
    rework_count INTEGER,
    scrap_count INTEGER,
    created_date TIMESTAMP
  ),
  grain (quality_id),
  audits (
    UNIQUE_VALUES(columns = (quality_id)),
    NOT_NULL(columns = (quality_id))
  )
);
