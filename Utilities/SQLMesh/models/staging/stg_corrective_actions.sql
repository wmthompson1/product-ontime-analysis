MODEL (
  name staging.stg_corrective_actions,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column target_date
  ),
  cron '@daily',
  grain (capa_id, ncm_id),
    partitioned_by (target_date),
  audits (
    UNIQUE_VALUES(columns = (capa_id)),
    NOT_NULL(columns = (capa_id))
  ),
  
);

SELECT
  capa_id,
  ncm_id,
  action_description,
  target_date,
  actual_date,
  effectiveness_score,
  status,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.corrective_actions
WHERE target_date BETWEEN @start_ds AND @end_ds;
