MODEL (
  name staging.stg_industry_benchmarks,
  kind SEED (
    path '$root/seeds/industry_benchmarks.csv'
  ),
  columns (
    benchmark_id TEXT,
    metric_name TEXT,
    benchmark_level TEXT,
    benchmark_value DOUBLE,
    industry_segment TEXT,
    source TEXT,
    year INTEGER,
    created_date TIMESTAMP
  ),
  grain (benchmark_id),
  audits (
    UNIQUE_VALUES(columns = (benchmark_id)),
    NOT_NULL(columns = (benchmark_id))
  )
);
