MODEL (
  name staging.stg_operation_routings,
  kind FULL,
  cron '@daily',
  columns (
    routing_id TEXT,
    product_id TEXT,
    op_sequence INT,
    work_center_id TEXT,
    setup_time DOUBLE,
    run_time DOUBLE
  ),
  grain (
    routing_id
  ),
  audits (UNIQUE_VALUES(columns = (
      routing_id
    )), NOT_NULL(columns = (
      routing_id
  )))
);

SELECT
  RoutingID::TEXT AS routing_id,
  ProductID::TEXT AS product_id,
  OperationSequence::INT AS op_sequence,
  WorkCenterID::TEXT AS work_center_id,
  SetupTime::DOUBLE AS setup_time,
  RunTime::DOUBLE AS run_time
FROM raw.operation_routings