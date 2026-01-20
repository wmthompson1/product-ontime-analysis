MODEL (
  name staging.stg_quality_costs,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column cost_date
  ),
  cron '@daily',
  grain (cost_id, product_line_id),
  audits (
    UNIQUE_VALUES(columns = (cost_id)),
    NOT_NULL(columns = (cost_id))
  )
);

SELECT
  cost_id,
  product_line_id,
  cost_date,
  cost_category,
  cost_subcategory,
  cost_amount,
  units_affected,
  cost_per_unit,
  cost_driver,
  prevention_opportunity,
  department_charged,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.quality_costs
WHERE cost_date BETWEEN @start_ds AND @end_ds;
