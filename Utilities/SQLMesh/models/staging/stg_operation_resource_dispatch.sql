MODEL (
  name staging.stg_operation_resource_dispatch,
  kind FULL,
  cron '@daily',
  columns (
    workorder_type       TEXT,
    workorder_base_id    TEXT,
    workorder_lot_id     TEXT,
    workorder_split_id   TEXT,
    workorder_sub_id     TEXT,
    sequence_no          INTEGER,
    resource_id          TEXT,
    dispatch_sequence    INTEGER
  ),
  grain (workorder_type, workorder_base_id, workorder_lot_id, workorder_split_id, workorder_sub_id, sequence_no, resource_id),
  audits (
    NOT_NULL(columns = (workorder_base_id, resource_id))
  )
);

SELECT
  CAST(WORKORDER_TYPE     AS TEXT)    AS workorder_type,
  CAST(WORKORDER_BASE_ID  AS TEXT)    AS workorder_base_id,
  CAST(WORKORDER_LOT_ID   AS TEXT)    AS workorder_lot_id,
  CAST(WORKORDER_SPLIT_ID AS TEXT)    AS workorder_split_id,
  CAST(WORKORDER_SUB_ID   AS TEXT)    AS workorder_sub_id,
  CAST(SEQUENCE_NO        AS INTEGER) AS sequence_no,
  CAST(RESOURCE_ID        AS TEXT)    AS resource_id,
  CAST(DISPATCH_SEQUENCE  AS INTEGER) AS dispatch_sequence
FROM raw.operation_resource_dispatch;
