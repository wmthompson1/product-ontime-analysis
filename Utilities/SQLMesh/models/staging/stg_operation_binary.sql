MODEL (
  name staging.stg_operation_binary,
  kind FULL,
  cron '@daily',
  columns (
    workorder_type       TEXT,
    workorder_base_id    TEXT,
    workorder_lot_id     TEXT,
    workorder_split_id   TEXT,
    workorder_sub_id     TEXT,
    sequence_no          INTEGER,
    type                 TEXT,
    bits_length          INTEGER
    -- bits (image/BLOB) excluded from staging layer
  ),
  grain (workorder_type, workorder_base_id, workorder_lot_id, workorder_split_id, workorder_sub_id, sequence_no, type),
  audits (
    NOT_NULL(columns = (workorder_base_id, sequence_no, type))
  )
);

SELECT
  CAST(WORKORDER_TYPE     AS TEXT)    AS workorder_type,
  CAST(WORKORDER_BASE_ID  AS TEXT)    AS workorder_base_id,
  CAST(WORKORDER_LOT_ID   AS TEXT)    AS workorder_lot_id,
  CAST(WORKORDER_SPLIT_ID AS TEXT)    AS workorder_split_id,
  CAST(WORKORDER_SUB_ID   AS TEXT)    AS workorder_sub_id,
  CAST(SEQUENCE_NO        AS INTEGER) AS sequence_no,
  CAST(TYPE               AS TEXT)    AS type,
  CAST(BITS_LENGTH        AS INTEGER) AS bits_length
FROM raw.operation_binary;
