MODEL (
  name staging.stg_financial_impact,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date
  ),
  cron '@daily',
  grain impact_id,
  audits (
    UNIQUE_VALUES(columns = (impact_id)),
    NOT_NULL(columns = (impact_id))
  )
);

SELECT
  impact_id,
  event_date,
  impact_type,
  impact_category,
  gross_impact,
  recovery_amount,
  net_impact,
  affected_product_lines,
  root_cause_category,
  business_unit,
  impact_duration_days,
  mitigation_cost,
  lessons_learned,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.financial_impact
WHERE event_date BETWEEN @start_ds AND @end_ds;
