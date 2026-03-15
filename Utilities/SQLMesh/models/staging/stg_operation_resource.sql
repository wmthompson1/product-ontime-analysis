MODEL (
  name staging.stg_operation_resource,
  kind FULL,
  cron '@daily',
  columns (
    workorder_type        TEXT,
    workorder_base_id     TEXT,
    workorder_lot_id      TEXT,
    workorder_split_id    TEXT,
    workorder_sub_id      TEXT,
    sequence_no           INTEGER,
    resource_id           TEXT,
    type                  TEXT,
    percent_duration      INTEGER,
    justification         TEXT,
    schedule_type         INTEGER,
    min_segment_size      DOUBLE,
    num_mem_to_sched      INTEGER,
    sched_equal_cap       TEXT,
    sched_start_date      TIMESTAMP,
    sched_finish_date     TIMESTAMP,
    sched_capacity_usage  INTEGER
  ),
  grain (workorder_type, workorder_base_id, workorder_lot_id, workorder_split_id, workorder_sub_id, sequence_no, resource_id),
  audits (
    NOT_NULL(columns = (workorder_base_id, resource_id))
  )
);

SELECT
  CAST(WORKORDER_TYPE       AS TEXT)      AS workorder_type,
  CAST(WORKORDER_BASE_ID    AS TEXT)      AS workorder_base_id,
  CAST(WORKORDER_LOT_ID     AS TEXT)      AS workorder_lot_id,
  CAST(WORKORDER_SPLIT_ID   AS TEXT)      AS workorder_split_id,
  CAST(WORKORDER_SUB_ID     AS TEXT)      AS workorder_sub_id,
  CAST(SEQUENCE_NO          AS INTEGER)   AS sequence_no,
  CAST(RESOURCE_ID          AS TEXT)      AS resource_id,
  CAST(TYPE                 AS TEXT)      AS type,
  CAST(PERCENT_DURATION     AS INTEGER)   AS percent_duration,
  CAST(JUSTIFICATION        AS TEXT)      AS justification,
  CAST(SCHEDULE_TYPE        AS INTEGER)   AS schedule_type,
  CAST(MIN_SEGMENT_SIZE     AS DOUBLE)    AS min_segment_size,
  CAST(NUM_MEM_TO_SCHED     AS INTEGER)   AS num_mem_to_sched,
  CAST(SCHED_EQUAL_CAP      AS TEXT)      AS sched_equal_cap,
  CAST(SCHED_START_DATE     AS TIMESTAMP) AS sched_start_date,
  CAST(SCHED_FINISH_DATE    AS TIMESTAMP) AS sched_finish_date,
  CAST(SCHED_CAPACITY_USAGE AS INTEGER)   AS sched_capacity_usage
FROM raw.operation_resource;
