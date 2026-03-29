MODEL (
  name staging.stg_operation_binary,
  kind FULL,
  cron '@daily',
  columns (
    workorder_type TEXT,
    workorder_base_id TEXT,
    workorder_lot_id TEXT,
    workorder_split_id TEXT,
    workorder_sub_id TEXT,
    sequence_no INT,
    type TEXT,
    bits_length INT
  ) /* bits (image/BLOB) excluded from staging layer */,
  grain (
    workorder_type,
    workorder_base_id,
    workorder_lot_id,
    workorder_split_id,
    workorder_sub_id,
    sequence_no,
    type
  ),
  audits (
    NOT_NULL(columns = (workorder_base_id, sequence_no, type))
  )
);

SELECT
  WORKORDER_TYPE::TEXT AS workorder_type,
  WORKORDER_BASE_ID::TEXT AS workorder_base_id,
  WORKORDER_LOT_ID::TEXT AS workorder_lot_id,
  WORKORDER_SPLIT_ID::TEXT AS workorder_split_id,
  WORKORDER_SUB_ID::TEXT AS workorder_sub_id,
  SEQUENCE_NO::INT AS sequence_no,
  TYPE::TEXT AS type,
  BITS_LENGTH::INT AS bits_length
FROM raw.operation_binary