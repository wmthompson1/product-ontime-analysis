MODEL (
  name staging.stg_operation_routings,
  kind FULL,
  cron '@daily',
  columns (
    routing_id    TEXT,
    product_id    TEXT,
    op_sequence   INTEGER,
    work_center_id TEXT,
    setup_time    DOUBLE,
    run_time      DOUBLE
  ),
  grain (routing_id),
  audits (
    UNIQUE_VALUES(columns = (routing_id)),
    NOT_NULL(columns = (routing_id))
  )
);

SELECT
  CAST(RoutingID          AS TEXT)    AS routing_id,
  CAST(ProductID          AS TEXT)    AS product_id,
  CAST(OperationSequence  AS INTEGER) AS op_sequence,
  CAST(WorkCenterID       AS TEXT)    AS work_center_id,
  CAST(SetupTime          AS DOUBLE)  AS setup_time,
  CAST(RunTime            AS DOUBLE)  AS run_time
FROM raw.operation_routings;
