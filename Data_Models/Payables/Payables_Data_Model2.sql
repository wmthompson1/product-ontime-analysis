--USE [DataWarehouse]
--GO


-- based on Supplier_Perf_Shafer_2018.sql
-- 1160-60
-- ATUR012022A0001

-- 167375
-- Exclude TMXDIV
-- START END
-- + only no minus's 

/**********************************************************************************************
Description:
0. payables flow with receivers flow 
1. grain of Received data should be by vendor, po, po line, and receiver
2. IQM grain is vendor, po, po line
3. Requirement change 8/12 will roll up 
4. Current versions of reports are probably not going to be in test plan

Note:
 previous processes and reports may have defects

Date    Modified By     Change Description
---------- ------------------ ------------------------------------------------------------
2025-08-11    William        Created - based on 750 Supplier_Perf_Shafer_2018.sql
2025-08-22    William      - adjusted due date  on_time_vs_late
2025-09-02    William      -= [sql-bi-1].DATAWAREHOUSE.DBO.

    1. Receiver.Received_Date for date range 
    2. Included in data 
    3. Vendor ID 
    4. PO# 
    5. PO Line  
    6. Receiver ID – From Purchase Receipt 
    7. Promise Date – From Purchase Order 
    8. Desired_Recv Date – from Purchase Order 
    9. Commodity Code – from part maintenance 
    10. Controlled – Part Maintenance |  
    11. Supplier Type -vendor maintenance 

  For vendor level reporting, we can roll up by vendor and ignore the po, po line, and receiver dimensions.
  Use AND R.RECEIVED_Date >= @START_DATE AND R.RECEIVED_Date <= @END_DATE to filter by date range.


**********************************************************************************************/


SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results

SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SET DEADLOCK_PRIORITY LOW;

DECLARE @PURC_ORDER_ID NVARCHAR(15);

DECLARE @VENDOR_ID NVARCHAR(255);

SET @VENDOR_ID = null;
SET @VENDOR_ID = NULL;
SET @PURC_ORDER_ID = null;

DECLARE @START_DATE DATE; 
DECLARE @END_DATE DATE;
SET @START_DATE = '2025-07-01';
SET @END_DATE = GETDATE();



    SELECT  
    
         --'Version 7/28 + - 1/1/25 - 6/30/25' NOTE
         PO.VENDOR_ID              --3 
        , POL.PURC_ORDER_ID      --4
        , convert(smallint, POL.LINE_NO) AS 'PURC_ORDER_LINE_NO'    -- 5.
        , POL.ORDER_QTY AS 'PO_LINE_ORDERQTY'
        , RL.RECEIVER_ID    -- 6.
        , RL.RECEIVED_Qty
        , pol.PROMISE_DATE
        , R.RECEIVED_Date

        -- adjusted_due_date
        ,convert(date,
          iif(pol.promise_DATE is null, pol.Desired_recv_date + 3, 
             iif (pol.promise_date >= pol.Desired_recv_date, pol.promise_date, pol.Desired_recv_date + 3))
          ) adjusted_due_date 

        -- on_time_vs_late
          ,convert(varchar(15),
             IIF(R.received_date <= (
               -- using adjusted_due_date
                 convert(date,
                  iif(pol.promise_DATE is null, pol.Desired_recv_date + 3, 
                     iif (pol.promise_date >= pol.Desired_recv_date, pol.promise_date, pol.Desired_recv_date + 3))
                     ) 

             ), 'On-time', 'Late')
                ) on_time_vs_late

        , pol.DESIRED_RECV_DATE -- 8.
        , POL.COMMODITY_CODE
                --, CONVERT(DATE, POL.DESIRED_RECV_DATE + 5, 101) as 'DUE_DATE'
        , UD.STRING_VAL AS CONTROLLED
        , V.USER_6 as SUPPLIER_TYPE
        , POL.PART_ID
        , PART.PLANNER_USER_ID
        , V.user_7 as PRODUCT_TYPE



    FROM PURC_ORDER_LINE POL
    INNER JOIN PURCHASE_ORDER PO ON POL.PURC_ORDER_ID = PO.ID
    INNER JOIN RECEIVER_LINE RL
        ON POL.PURC_ORDER_ID = RL.PURC_ORDER_ID
        AND POL.LINE_NO = RL.PURC_ORDER_LINE_NO AND RL.RECEIVED_QTY > 0 -- UPD 8/7
    INNER JOIN RECEIVER R  ON RL.RECEIVER_ID = R.ID


    -- LEFT JOIN Datamart.dbo.SKILLS_PART_UDF SKILLS_PART_UDF 
    -- ON POL.PART_ID=SKILLS_PART_UDF.PART_ID

    left JOIN.PART 
    ON PART.ID = POL.PART_ID

    left JOIN VENDOR V
    ON PO.VENDOR_ID = V.ID

    LEFT JOIN USER_DEF_FIELDS UD 
    ON POL.PART_ID = UD.DOCUMENT_ID 
    AND UD.ID = 'UDF-0000082' AND UD.PROGRAM_ID = 'VMPRTMNT'

    WHERE (1=1)
    and (PO.VENDOR_ID = @VENDOR_ID
         OR @VENDOR_ID IS NULL)
        AND V.ID != 'TMXDIV'
     --   AND 
        --(POL.PURC_ORDER_ID = @PURC_ORDER_ID
        --   OR @PURC_ORDER_ID IS NULL)
                AND R.RECEIVED_Date >= @START_DATE AND R.RECEIVED_Date <= @END_DATE


ORDER BY PURC_ORDER_ID, VENDOR_ID,PURC_ORDER_LINE_NO
;



