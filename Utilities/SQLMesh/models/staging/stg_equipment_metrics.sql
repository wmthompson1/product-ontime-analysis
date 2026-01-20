MODEL (
  name staging.stg_equipment_metrics,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column measurement_date
  ),
  cron '@daily',
  grain (equipment_id, line_id),
    partitioned_by (measurement_date),
    audits (
      UNIQUE_VALUES(columns = (equipment_id)),
      NOT_NULL(columns = (equipment_id))
    ),
  columns (
    measurement_date "partition key",
    availability_rate "Equipment availability (OEE component)",
    performance_rate "Equipment performance (OEE component)",
    quality_rate "Equipment quality rate (OEE component)",
    oee_score "Overall Equipment Effectiveness (0-100%)",
    downtime_hours "Downtime duration in hours"
  )
);

SELECT
  equipment_id,
  line_id,
  equipment_type,
  equipment_name,
  measurement_date,
  availability_rate,
  performance_rate,
  quality_rate,
  oee_score,
  downtime_hours,
  COALESCE(created_date, CURRENT_TIMESTAMP) AS created_date
FROM raw.equipment_metrics
WHERE measurement_date BETWEEN @start_ds AND @end_ds;
