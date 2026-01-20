MODEL (
  name staging.stg_non_conformant_materials,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column incident_date
  ),
  cron '@daily',
  grain (ncm_id, supplier_id),
  partitioned_by (incident_date),
  audits (
    UNIQUE_VALUES(columns = (ncm_id)),
    NOT_NULL(columns = (ncm_id))
  ),
  columns (
    incident_date "partition key",
    severity "Severity classification (Critical/Major/Minor)",
    cost_impact "Financial impact in dollars"
  )
);

SELECT
  ncm_id,
  incident_date,
  product_line,
  supplier_id,
  material_type,
  defect_description,
  quantity_affected,
  severity,
  root_cause,
  cost_impact,
  status,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.non_conformant_materials
WHERE incident_date BETWEEN @start_ds AND @end_ds;
