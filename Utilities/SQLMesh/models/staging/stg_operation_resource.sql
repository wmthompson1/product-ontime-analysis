MODEL (
  name staging.stg_operation_resource,
  kind FULL,
  cron '@daily',
  columns (
    workorder_type TEXT,
    workorder_base_id TEXT,
    workorder_lot_id TEXT,
    workorder_split_id TEXT,
    workorder_sub_id TEXT,
    sequence_no INT,
    resource_id TEXT,
    type TEXT,
    percent_duration INT,
    justification TEXT,
    schedule_type INT,
    min_segment_size DOUBLE,
    num_mem_to_sched INT,
    sched_equal_cap TEXT,
    sched_start_date TIMESTAMP,
    sched_finish_date TIMESTAMP,
    sched_capacity_usage INT
  ),
  grain (
    workorder_type,
    workorder_base_id,
    workorder_lot_id,
    workorder_split_id,
    workorder_sub_id,
    sequence_no,
    resource_id
  ),
  audits (
    NOT_NULL(columns = (workorder_base_id, resource_id))
  )
);

SELECT
  WORKORDER_TYPE::TEXT AS workorder_type,
  WORKORDER_BASE_ID::TEXT AS workorder_base_id,
  WORKORDER_LOT_ID::TEXT AS workorder_lot_id,
  WORKORDER_SPLIT_ID::TEXT AS workorder_split_id,
  WORKORDER_SUB_ID::TEXT AS workorder_sub_id,
  SEQUENCE_NO::INT AS sequence_no,
  RESOURCE_ID::TEXT AS resource_id,
  TYPE::TEXT AS type,
  PERCENT_DURATION::INT AS percent_duration,
  JUSTIFICATION::TEXT AS justification,
  SCHEDULE_TYPE::INT AS schedule_type,
  MIN_SEGMENT_SIZE::DOUBLE AS min_segment_size,
  NUM_MEM_TO_SCHED::INT AS num_mem_to_sched,
  SCHED_EQUAL_CAP::TEXT AS sched_equal_cap,
  SCHED_START_DATE::TIMESTAMP AS sched_start_date,
  SCHED_FINISH_DATE::TIMESTAMP AS sched_finish_date,
  SCHED_CAPACITY_USAGE::INT AS sched_capacity_usage
FROM raw.operation_resource