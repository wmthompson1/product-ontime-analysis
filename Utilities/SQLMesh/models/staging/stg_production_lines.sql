MODEL (
  name staging.stg_production_lines,
  kind FULL,
  grain (line_id),
  audits (
    UNIQUE_VALUES(columns = (line_id)),
    NOT_NULL(columns = (line_id))
  ),
  
);

SELECT
  line_id,
  line_name,
  facility_location,
  line_type,
  theoretical_capacity,
  actual_capacity,
  efficiency_rating,
  installation_date,
  last_maintenance_date,
  status,
  supervisor,
  COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
FROM raw.production_lines;
