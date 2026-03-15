MODEL (
  name staging.stg_operation_summary,
  kind FULL,
  cron '@daily',
  columns (
    spid                 TEXT,
    workorder_type       TEXT,
    workorder_base_id    TEXT,
    workorder_lot_id     TEXT,
    workorder_split_id   TEXT,
    workorder_sub_id     TEXT,
    sequence_no          INTEGER,
    est_atl_lab_cost     DOUBLE,
    est_atl_bur_cost     DOUBLE,
    est_atl_ser_cost     DOUBLE,
    rem_atl_lab_cost     DOUBLE,
    rem_atl_bur_cost     DOUBLE,
    rem_atl_ser_cost     DOUBLE,
    run_hrs              DOUBLE,
    status               TEXT,
    setup_completed      TEXT
  ),
  grain (spid, workorder_type, workorder_base_id, workorder_lot_id, workorder_split_id, workorder_sub_id, sequence_no),
  audits (
    NOT_NULL(columns = (spid, workorder_base_id))
  )
);

SELECT
  CAST(SPID               AS TEXT)   AS spid,
  CAST(WORKORDER_TYPE     AS TEXT)   AS workorder_type,
  CAST(WORKORDER_BASE_ID  AS TEXT)   AS workorder_base_id,
  CAST(WORKORDER_LOT_ID   AS TEXT)   AS workorder_lot_id,
  CAST(WORKORDER_SPLIT_ID AS TEXT)   AS workorder_split_id,
  CAST(WORKORDER_SUB_ID   AS TEXT)   AS workorder_sub_id,
  CAST(SEQUENCE_NO        AS INTEGER) AS sequence_no,
  CAST(EST_ATL_LAB_COST   AS DOUBLE) AS est_atl_lab_cost,
  CAST(EST_ATL_BUR_COST   AS DOUBLE) AS est_atl_bur_cost,
  CAST(EST_ATL_SER_COST   AS DOUBLE) AS est_atl_ser_cost,
  CAST(REM_ATL_LAB_COST   AS DOUBLE) AS rem_atl_lab_cost,
  CAST(REM_ATL_BUR_COST   AS DOUBLE) AS rem_atl_bur_cost,
  CAST(REM_ATL_SER_COST   AS DOUBLE) AS rem_atl_ser_cost,
  CAST(RUN_HRS            AS DOUBLE) AS run_hrs,
  CAST(STATUS             AS TEXT)   AS status,
  CAST(SETUP_COMPLETED    AS TEXT)   AS setup_completed
FROM raw.operation_summary;
