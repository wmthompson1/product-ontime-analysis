
-- 

/**
  M 313Z7430-504
313Z7430-504
1803245.1/3

**/

/****************************report*****************************************************************
blank operations for manuf after Feb 1
William 3/4

Use Casae - ticket
  M 313Z7430-504
313Z7430-504
1803245.1/3

-- **********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results;

SELECT TOP (10000) 
'Op Binary (OB) record missing' note
--o.[ROWID]
      ,o.[STATUS_EFF_DATE]
      ,o.[STATUS] OPERATION_STATUS
      ,o.[WORKORDER_TYPE]
      ,o.[WORKORDER_BASE_ID]
      ,o.[WORKORDER_LOT_ID]
      ,o.[WORKORDER_SPLIT_ID]
      ,o.[WORKORDER_SUB_ID]
      ,o.[SEQUENCE_NO]
	  
	  -- OB_
  ,isnull(ob.WORKORDER_BASE_ID,'<blank>')  OB_WORKORDER_BASE_ID
  ,isnull(ob.WORKORDER_LOT_ID,'-')   OB_WORKORDER_LOT_ID 
  ,isnull(ob.WORKORDER_SPLIT_ID, '-') OB_WORKORDER_SPLIT_ID
  ,isnull(ob.WORKORDER_SUB_ID, '-')   OB_WORKORDER_SUB_ID
  ,isnull(ob.WORKORDER_TYPE, '-')     OB_WORKORDER_TYPE
  ,ob.SEQUENCE_NO      OB_SEQUENCE_NO
	  
      ,o.[RESOURCE_ID]
      ,o.[SETUP_HRS]
      ,o.[RUN]
      ,o.[RUN_TYPE]
      --,o.[LOAD_SIZE_QTY]
      --,o.[RUN_HRS]
      --,o.[MOVE_HRS]
      --,o.[TRANSIT_DAYS]
      --,o.[SERVICE_ID]
      --,o.[SCRAP_YIELD_PCT]
      --,o.[SCRAP_YIELD_TYPE]
      --,o.[FIXED_SCRAP_UNITS]
      --,o.[MINIMUM_MOVE_QTY]
      --,o.[CALC_START_QTY]
      --,o.[CALC_END_QTY]
      --,o.[COMPLETED_QTY]
      --,o.[DEVIATED_QTY]
      --,o.[ACT_SETUP_HRS]
      --,o.[ACT_RUN_HRS]

      --,o.[SETUP_COMPLETED]
      --,o.[SERVICE_BEGIN_DATE]
      ,o.[CLOSE_DATE]
      ,o.[OPERATION_TYPE]
      --,o.[DRAWING_ID]
      --,o.[DRAWING_REV_NO]
      --,o.[OVERRIDE_QTYS]
      --,o.[BEGIN_TRACEABILITY]
      --,o.[CAPACITY_USAGE_MAX]
      --,o.[CAPACITY_USAGE_MIN]
      --,o.[TEST_ID]
      --,o.[SPC_QTY]
      --,o.[SCHED_START_DATE]
      --,o.[SCHED_FINISH_DATE]
      --,o.[COULD_FINISH_DATE]
      --,o.[ISDETERMINANT]
      --,o.[SETUP_COST_PER_HR]
      --,o.[RUN_COST_PER_HR]
      --,o.[RUN_COST_PER_UNIT]
      --,o.[BUR_PER_HR_SETUP]
      --,o.[BUR_PER_HR_RUN]
      --,o.[BUR_PER_UNIT_RUN]
      --,o.[SERVICE_BASE_CHG]
      --,o.[BUR_PERCENT_SETUP]
      --,o.[BUR_PERCENT_RUN]
      --,o.[BUR_PER_OPERATION]
      --,o.[EST_ATL_LAB_COST]
      --,o.[EST_ATL_BUR_COST]
      --,o.[EST_ATL_SER_COST]
      --,o.[REM_ATL_LAB_COST]
      --,o.[REM_ATL_BUR_COST]
      --,o.[REM_ATL_SER_COST]
      --,o.[ACT_ATL_LAB_COST]
      --,o.[ACT_ATL_BUR_COST]
      --,o.[ACT_ATL_SER_COST]
      --,o.[EST_TTL_MAT_COST]
      --,o.[EST_TTL_LAB_COST]
      --,o.[EST_TTL_BUR_COST]
      --,o.[EST_TTL_SER_COST]
      --,o.[REM_TTL_MAT_COST]
      --,o.[REM_TTL_LAB_COST]
      --,o.[REM_TTL_BUR_COST]
      --,o.[REM_TTL_SER_COST]
      --,o.[ACT_TTL_MAT_COST]
      --,o.[ACT_TTL_LAB_COST]
      --,o.[ACT_TTL_BUR_COST]
      --,o.[ACT_TTL_SER_COST]
      --,o.[SPLIT_ADJUSTMENT]
      --,o.[MILESTONE_ID]
      --,o.[SCHEDULE_TYPE]
      --,o.[MIN_SEGMENT_SIZE]
      --,o.[PROTECT_COST]
      --,o.[DRAWING_FILE]
      --,o.[DISPATCHED_QTY]
      --,o.[SERVICE_MIN_CHG]
      --,o.[VENDOR_ID]
      --,o.[VENDOR_SERVICE_ID]
      --,o.[SERVICE_PART_ID]
      --,o.[LAST_DISP_DATE]
      --,o.[LAST_RECV_DATE]
      --,o.[WAREHOUSE_ID]
      --,o.[ALLOCATED_QTY]
      --,o.[FULFILLED_QTY]
      --,o.[LEAST_MIN_MOVE_QTY]
      --,o.[MAX_GAP_PREV_OP]
      --,o.[APPLY_CALENDAR]
      --,o.[MAX_DOWNTIME]
      --,o.[ACCUM_DOWNTIME]
      --,o.[RUN_QTY_PER_CYCLE]
      --,o.[USER_1]
      --,o.[USER_2]
      --,o.[USER_3]
      --,o.[USER_4]
      --,o.[USER_5]
      --,o.[USER_6]
      --,o.[USER_7]
      --,o.[USER_8]
      --,o.[USER_9]
      --,o.[USER_10]
      --,o.[UDF_LAYOUT_ID]
      --,o.[NUM_MEM_TO_SCHED]
      --,o.[SERVICE_BUFFER]
      --,o.[MILESTONE_SUB_ID]
      --,o.[POST_MILESTONE]
      --,o.[PROJ_MILESTONE_OP]
      --,o.[WBS_CODE]
      --,o.[WBS_START_DATE]
      --,o.[WBS_END_DATE]
      --,o.[WBS_DURATION]
      --,o.[MILESTONE_SEQ_NO]
      --,o.[PRD_INSP_PLAN_ID]
      --,o.[SETUP_INSPECT_REQ]
      --,o.[RUN_INSPECT_REQ]
   
      --,o.[PRED_SUB_ID]
      --,o.[PRED_SEQ_NO]
      --,o.[SITE_ID]
      --,o.[SCHED_CAPACITY_USAGE]
      --,o.[BID_RATE_CATEGORY_ID]
      --,o.[OVERLAP_SETUP]
      --,o.[PERCENT_COMPL]
      --,o.[QTY_COMPL_BY_HRS]
      --,o.[MAX_QTY_COMPLETE]
      --,o.[DISPATCH_SEQUENCE]
      --,o.[COMB_DISP_SEQUENCE]
  FROM [LIVE].[dbo].[OPERATION] o

      JOIN dbo.OPERATION_TYPE ot
      ON o.OPERATION_TYPE = ot.ID
    -- AND o.RESOURCE_ID    = ot.RESOURCE_ID

    JOIN dbo.OPER_TYPE_BINARY otb
      ON otb.OPERATION_TYPE_ID = o.OPERATION_TYPE

    LEFT JOIN dbo.OPERATION_BINARY ob
      ON ob.WORKORDER_BASE_ID = o.WORKORDER_BASE_ID
     AND ob.WORKORDER_LOT_ID  = o.WORKORDER_LOT_ID
     AND ob.WORKORDER_SPLIT_ID= o.WORKORDER_SPLIT_ID
     AND ob.WORKORDER_SUB_ID  = o.WORKORDER_SUB_ID
     AND ob.WORKORDER_TYPE    = o.WORKORDER_TYPE
     AND ob.SEQUENCE_NO       = o.SEQUENCE_NO



  where 1=1 
  and o.STATUS_EFF_DATE >= '2026-02-01'
  and o.WORKORDER_TYPE = 'W'
  --and o.[WORKORDER_BASE_ID] = '1803245'
  --and o.SEQUENCE_NO in (490,480)
  and o.[WORKORDER_SPLIT_ID] < 6

  and ob.WORKORDER_BASE_ID 		is null
  and ob.WORKORDER_LOT_ID  		is null
  and ob.WORKORDER_SPLIT_ID		is null
  and ob.WORKORDER_SUB_ID  		is null
  and ob.WORKORDER_TYPE         is null
  and ob.SEQUENCE_NO            is null


  order by
       o.[WORKORDER_BASE_ID]
	  ,o.[WORKORDER_LOT_ID]
      ,o.[WORKORDER_SPLIT_ID]
	  ,o.[SEQUENCE_NO] 


      ,o.[WORKORDER_SUB_ID]
	  ,o.WORKORDER_TYPE
	  ,o.STATUS_EFF_DATE
 