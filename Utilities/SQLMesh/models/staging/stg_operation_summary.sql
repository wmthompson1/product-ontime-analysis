MODEL (
  name staging.stg_operation_summary,
  kind FULL,
  cron '@daily',
  columns (
    spid TEXT,
    workorder_type TEXT,
    workorder_base_id TEXT,
    workorder_lot_id TEXT,
    workorder_split_id TEXT,
    workorder_sub_id TEXT,
    sequence_no INT,
    est_atl_lab_cost DOUBLE,
    est_atl_bur_cost DOUBLE,
    est_atl_ser_cost DOUBLE,
    rem_atl_lab_cost DOUBLE,
    rem_atl_bur_cost DOUBLE,
    rem_atl_ser_cost DOUBLE,
    run_hrs DOUBLE,
    status TEXT,
    setup_completed TEXT
  ),
  grain (
    spid,
    workorder_type,
    workorder_base_id,
    workorder_lot_id,
    workorder_split_id,
    workorder_sub_id,
    sequence_no
  ),
  audits (
    NOT_NULL(columns = (spid, workorder_base_id))
  )
);

SELECT
  SPID::TEXT AS spid,
  WORKORDER_TYPE::TEXT AS workorder_type,
  WORKORDER_BASE_ID::TEXT AS workorder_base_id,
  WORKORDER_LOT_ID::TEXT AS workorder_lot_id,
  WORKORDER_SPLIT_ID::TEXT AS workorder_split_id,
  WORKORDER_SUB_ID::TEXT AS workorder_sub_id,
  SEQUENCE_NO::INT AS sequence_no,
  EST_ATL_LAB_COST::DOUBLE AS est_atl_lab_cost,
  EST_ATL_BUR_COST::DOUBLE AS est_atl_bur_cost,
  EST_ATL_SER_COST::DOUBLE AS est_atl_ser_cost,
  REM_ATL_LAB_COST::DOUBLE AS rem_atl_lab_cost,
  REM_ATL_BUR_COST::DOUBLE AS rem_atl_bur_cost,
  REM_ATL_SER_COST::DOUBLE AS rem_atl_ser_cost,
  RUN_HRS::DOUBLE AS run_hrs,
  STATUS::TEXT AS status,
  SETUP_COMPLETED::TEXT AS setup_completed
FROM raw.operation_summary