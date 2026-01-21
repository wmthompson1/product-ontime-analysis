MODEL (
  name staging.stg_industry_benchmarks,
  kind SEED (
    path '$root/seeds/industry_benchmarks.csv'
  ),
  grain (benchmark_id),
  audits (
    UNIQUE_VALUES(columns = (benchmark_id)),
    NOT_NULL(columns = (benchmark_id))
  )
);
