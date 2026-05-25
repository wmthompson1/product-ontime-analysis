USE [LIVE]; -- lab2
GO

-- REPORTS\...\10 wods code block - manufacturing\10_Workorder_MfgV2.sql
-- 10_Workorder_MfgV2.sql

-- Script #1: 10_Workorder_MfgV2.sql ==>>  Staging.dbo.WODS_Comp_test223
/****

'Wods light needed to test'
4/17/2026 add CurrentOperation

-- into compl
FROM Staging.dbo.Comp_test222

	FROM Staging.dbo.WODS_Comp_test223 a WITH (NOLOCK) 
		
	/*Join to add Raw Material*/
	LEFT JOIN (
		SELECT WO, LOT, SPLIT, SUM(available) as 'available', 
			SUM(REQ_QTY) as 'REQ_QTY', SUM(ISSUED_QTY) as 'ISSUED_QTY'
		FROM #RAW_MATERIAL_WODs
		group by WO, LOT, SPLIT


=IIF(Parameters!SortByDefault.Value="WAIT_DAYS",Fields(Parameters!SortByDefault.Value).Value,0)		-- Z to A
=IIF(IsNothing(Fields!EXP_FLT.Value), "6", Fields!EXP_FLT.Value)									-- A TO Z
=IIF(Parameters!SortByDefault.Value <> "WAIT_DAYS",Fields(Parameters!SortByDefault.Value).Value,0)  -- DUE DATE

****/


SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;

declare @base_id nvarchar(50) = NULL; -- -- '1789451'; -- '1781081'; --- '1795631';  --- '1736441';

-- -- DROP TABLE Staging.dbo.WODS_Comp_test223
IF OBJECT_ID('Staging.dbo.WODS_Comp_test223') IS NOT NULL DROP TABLE Staging.dbo.WODS_Comp_test223
IF OBJECT_ID('tempdb..#USER_DEF_FIELDS_W_48') IS NOT NULL DROP TABLE #USER_DEF_FIELDS_W_48

/* create USER_DEF_FIELDS_W_48 explicitly typed  */
-- records from udf must be explicitly typed
CREATE TABLE #USER_DEF_FIELDS_W_48
	([TYPE] NCHAR(1) NOT NULL
		, [BASE_ID] NVARCHAR(30) NOT NULL
		, [LOT_ID] NVARCHAR(3) NOT NULL
		, [SPLIT_ID] NVARCHAR(3) NOT NULL
		, [SUB_ID] NVARCHAR(3) NOT NULL
		, [PROGRAM_ID] NVARCHAR(30) NOT NULL
		, [ID] NVARCHAR(30) NOT NULL
		, [LABEL] NVARCHAR(254)
		, [BOOL_VAL] INT
	)

INSERT INTO #USER_DEF_FIELDS_W_48 ( [TYPE], BASE_ID, LOT_ID, SUB_ID, SPLIT_ID 	
		, [PROGRAM_ID], [ID], [LABEL], [BOOL_VAL]  
	)
SELECT [TYPE] = SUBSTRING(ud.DOCUMENT_ID, 0, CHARINDEX(N'~',ud.DOCUMENT_ID))
		, BASE_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) - CHARINDEX(N'~', ud.DOCUMENT_ID) - 1) 
		, LOT_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) + 1) + 1, 1)
		, SUB_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) + 1, 1) 
		, SPLIT_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~',ud.DOCUMENT_ID, CHARINDEX(N'~',ud.DOCUMENT_ID) + 1) + 1) + 1) + 1, 1) 
		, ud.PROGRAM_ID, ud.ID, ud.[LABEL], ud.BOOL_VAL
FROM USER_DEF_FIELDS ud
WHERE ud.PROGRAM_ID = N'VMMFGWIN_OP' AND ud.ID = N'UDF-0000048' 
		AND ud.[LABEL] IS NULL  AND ud.BOOL_VAL = 1

CREATE NONCLUSTERED INDEX N2CIDX_UDF_w_48 ON #USER_DEF_FIELDS_W_48 	
	(BASE_ID, LOT_ID, SUB_ID, SPLIT_ID, [TYPE])

CREATE NONCLUSTERED INDEX NCIDX_UDF_w_48 ON #USER_DEF_FIELDS_W_48 (PROGRAM_ID) 
INCLUDE (ID, [LABEL], BOOL_VAL)

;WITH
-- 1) Filtered work orders (only the rows you care about)
WO AS
(
    SELECT *
    FROM dbo.WORK_ORDER
    WHERE [STATUS] IN (N'R', N'F', N'U')
      AND [TYPE]   = N'W'

),

-- 2) End-item row per (type, base, lot, split) where SUB_ID = '0'
EndItem AS
(
    SELECT wo.[TYPE], wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID, wo.PART_ID, wo.CREATE_DATE, wo.CLOSE_DATE
    FROM dbo.WORK_ORDER wo
	JOIN WO filt 
	        ON  filt.[TYPE]    = wo.[TYPE]
        AND filt.BASE_ID   = wo.BASE_ID
        AND filt.LOT_ID    = wo.LOT_ID
        AND filt.SPLIT_ID  = wo.SPLIT_ID
        AND filt.SUB_ID    = wo.SUB_ID
		
    WHERE wo.[TYPE] = N'W'
      AND wo.SUB_ID = N'0'
),

-- 3) Resolve rework part once
ResolvedWO AS
(
    SELECT
        wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID, wo.[TYPE],
        wo.PART_ID, wo.close_date,
        ResolvedPartID = IIF(wo.PART_ID like '%REWORK%', ei.PART_ID, wo.PART_ID),
        wo.DESIRED_QTY, wo.[STATUS],
        wo.PRINTED_DATE, wo.DESIRED_RLS_DATE, wo.CREATE_DATE
		,wo.DESIRED_WANT_DATE
		
    FROM WO AS wo
    LEFT JOIN EndItem AS ei
        ON  ei.[TYPE]    = wo.[TYPE]
        AND ei.BASE_ID   = wo.BASE_ID
        AND ei.LOT_ID    = wo.LOT_ID
        AND ei.SPLIT_ID  = wo.SPLIT_ID
        AND ei.SUB_ID    = N'0'
),

-- 4) Demand/Supply link + Customer Order / Line
DemandJoin AS
(
    SELECT
        dsl.SUPPLY_BASE_ID, dsl.SUPPLY_LOT_ID, dsl.SUPPLY_SPLIT_ID,
        dsl.DEMAND_BASE_ID, dsl.DEMAND_SEQ_NO, dsl.DEMAND_TYPE,
        col.CUST_ORDER_ID, col.LINE_NO, col.USER_10, col.USER_1,
        col.UNIT_PRICE, col.TOTAL_AMT_SHIPPED, col.TOTAL_AMT_ORDERED AS COL_AMOUNT,
        co.CUSTOMER_ID, co.CUSTOMER_PO_REF, co.TOTAL_AMT_ORDERED      AS CO_AMOUNT,
        co.CREATE_DATE AS CUST_ORD_CREATEDATE
    FROM dbo.DEMAND_SUPPLY_LINK AS dsl
    LEFT JOIN dbo.CUST_ORDER_LINE AS col
        ON  col.CUST_ORDER_ID = dsl.DEMAND_BASE_ID
        AND col.LINE_NO       = dsl.DEMAND_SEQ_NO
        AND dsl.DEMAND_TYPE   = N'CO'
    LEFT JOIN dbo.CUSTOMER_ORDER AS co
        ON  co.ID = col.CUST_ORDER_ID
),

-- 5) Part/site details for both the WO part and the End-item part
PartSite AS
(
    SELECT PART_ID, SITE_ID, QTY_ON_HAND, QTY_IN_DEMAND, BUYER_USER_ID, RTRIM(PLANNER_USER_ID) AS PLANNER_USER_ID,
           COMMODITY_CODE, [DESCRIPTION]
    FROM dbo.PART_SITE_VIEW
    WHERE SITE_ID = N'SK01'
),

-- 6) User-defined fields (Material, Alloy). If you have a tie-breaker column, ORDER BY it.
MaterialUDF AS
(
    SELECT pud2.DOCUMENT_ID AS PART_ID, NULLIF(pud2.STRING_VAL,'') AS Material
    FROM dbo.USER_DEF_FIELDS AS pud2
    WHERE pud2.PROGRAM_ID = N'VMPRTMNT'
      AND pud2.ID IN (N'UDF-0000035')      -- Material
      AND pud2.DOCUMENT_ID IS NOT NULL
),
AlloyUDF AS
(
    SELECT pud3.DOCUMENT_ID AS PART_ID, NULLIF(pud3.STRING_VAL,'') AS Alloy
    FROM dbo.USER_DEF_FIELDS AS pud3
    WHERE pud3.PROGRAM_ID = N'VMPRTMNT'
      AND pud3.ID IN (N'UDF-0000036')      -- Alloy
      AND pud3.DOCUMENT_ID IS NOT NULL
),
USER_DEF_FIELDS_W_48 as
(
select * from
#user_def_fields_w_48
)

SELECT
    start_date =
        COALESCE(rwo.DESIRED_RLS_DATE,
                 (SELECT W.DESIRED_RLS_DATE
                  FROM dbo.WORK_ORDER AS W
                  WHERE W.[TYPE]=rwo.[TYPE] AND W.BASE_ID=rwo.BASE_ID
                    AND W.LOT_ID=rwo.LOT_ID AND W.SPLIT_ID=rwo.SPLIT_ID AND W.SUB_ID=N'0')),
    CLOSE_DATE = rwo.CLOSE_DATE,
	DESIRED_WANT_DATE =
        ISNULL(
            rwo.DESIRED_WANT_DATE,
            (SELECT MIN(DESIRED_WANT_DATE)
             FROM dbo.WORK_ORDER AS w
             WHERE w.[TYPE]=rwo.[TYPE]
               AND w.BASE_ID=rwo.BASE_ID
               AND w.LOT_ID=rwo.LOT_ID
               AND w.SPLIT_ID=rwo.SPLIT_ID
               AND w.SUB_ID<>rwo.SUB_ID)  -- TODO
        ),
   [EXP/FLT] =

        coalesce(
        (SELECT TOP (1)
		COALESCE(ud.STRING_VAL,'6')
         FROM dbo.USER_DEF_FIELDS AS ud
         WHERE ud.PROGRAM_ID = N'VMMFGWIN_WO'
           AND ud.ID = N'UDF-0000070'
           AND ISNULL(ud.LABEL, N'') = N''
           AND (rwo.[TYPE] + N'~' + rwo.BASE_ID + N'~' + N'0' + N'~' + rwo.LOT_ID + N'~' + rwo.SPLIT_ID) = ud.DOCUMENT_ID)
		   ,'6')
		   
		   ,
    rwo.BASE_ID,
    rwo.LOT_ID,
    rwo.SPLIT_ID,
    rwo.SUB_ID,
    rwo.[TYPE],

    -- Resolved PART_ID (rework aware)
    IIF(rwo.PART_ID = N'REWORK MFG', ei.PART_ID, rwo.PART_ID) AS PART_ID,

    -- WONUM (choose Option A or B)
    -- A) Scalar UDF:
    -- dbo.sfnWONUMFormat(rwo.BASE_ID, rwo.LOT_ID, rwo.SPLIT_ID, rwo.SUB_ID) AS WONUM
    -- B) Inline TVF:
    --won.WONUM,

    rwo.DESIRED_QTY,
    rwo.[STATUS],

    dj.CUST_ORDER_ID   AS CUSTOMER_ORDER,
    dj.LINE_NO,

    -- CUSTOMER_ID derivations (kept as-is; mildly tidied)
    CUSTOMER_ID2 = IIF(
        dj.DEMAND_BASE_ID IS NULL AND dj.DEMAND_SEQ_NO IS NULL AND dj.DEMAND_TYPE IS NULL
        AND NULLIF(LTRIM(RTRIM(dj.CUSTOMER_ID)),'') IS NULL,
        CASE
            WHEN ISNUMERIC(SUBSTRING(ps.BUYER_USER_ID, 4, 1)) = 1 THEN N'BOEPOP'
            WHEN SUBSTRING(ps.BUYER_USER_ID, 4, 3) = N'DEF'     THEN N'BOEDEF'
            WHEN SUBSTRING(ps.BUYER_USER_ID, 4, 6) = N'SPIMOR'  THEN N'SPIMOR'
            WHEN SUBSTRING(ps.BUYER_USER_ID, 4, 3) = N'SPI'     THEN N'SPIAER'
            WHEN SUBSTRING(ps.BUYER_USER_ID, 4, 4) = N'CMPF'    THEN ps.PLANNER_USER_ID
            ELSE SUBSTRING(ps.BUYER_USER_ID, 4, 6)
        END,
        dj.CUSTOMER_ID
    ),

    CUSTOMER_ID = IIF(
        dj.DEMAND_BASE_ID IS NULL AND dj.DEMAND_SEQ_NO IS NULL AND dj.DEMAND_TYPE IS NULL
        AND NULLIF(LTRIM(RTRIM(dj.CUSTOMER_ID)),'') IS NULL,
        CASE
            WHEN ISNUMERIC(SUBSTRING(eps.BUYER_USER_ID, 4, 1)) = 1 THEN N'BOEPOP'
            WHEN SUBSTRING(eps.BUYER_USER_ID, 4, 3) = N'DEF'     THEN N'BOEDEF'
            WHEN SUBSTRING(ps.BUYER_USER_ID, 4, 6) = N'SPIMOR'   THEN N'SPIMOR'   -- original logic
            WHEN SUBSTRING(eps.BUYER_USER_ID, 4, 3) = N'SPI'     THEN N'SPIAER'
            WHEN SUBSTRING(eps.BUYER_USER_ID, 4, 4) = N'CMPF'    THEN eps.PLANNER_USER_ID
            ELSE SUBSTRING(eps.BUYER_USER_ID, 4, 6)
        END,
        dj.CUSTOMER_ID
    ),

    EndItem_Part_id        = ei.PART_ID,
    EndItem_Buyer_User_ID  = eps.BUYER_USER_ID,

    Allocation_Type = CASE
        WHEN dj.DEMAND_BASE_ID IS NULL AND dj.DEMAND_SEQ_NO IS NULL AND dj.DEMAND_TYPE IS NULL
        THEN N'Unlinked' END,

    buyer_ptr = SUBSTRING(ps.BUYER_USER_ID, 4, 1),

    -- Keep your existing scalar UDFs; see notes below for potential conversions
    dbo.sfn_current_operation(rwo.[TYPE], rwo.BASE_ID, rwo.LOT_ID, rwo.SPLIT_ID, rwo.SUB_ID) AS CurrentOperation,
    ISNULL(
        dbo.sfn_getlastopcompleted(rwo.[TYPE], rwo.BASE_ID, rwo.LOT_ID, rwo.SPLIT_ID, rwo.SUB_ID),
        dbo.ufn_GetFirstOperation(rwo.BASE_ID, rwo.LOT_ID, rwo.SUB_ID, rwo.SPLIT_ID, rwo.[TYPE])
    ) AS StatusCurrOp,

    rwo.PRINTED_DATE,



    CREATE_DATE = ISNULL(dj.CUST_ORD_CREATEDATE, rwo.CREATE_DATE),

    remaining_operations =
        ISNULL(dbo.sfn_remaining_operations(rwo.[TYPE], rwo.BASE_ID, rwo.LOT_ID, rwo.SPLIT_ID, rwo.SUB_ID),
               N'No Remaining Operations'),

    ps.QTY_ON_HAND,
    ps.QTY_IN_DEMAND,
    ps.BUYER_USER_ID,
    ps.PLANNER_USER_ID,
    ps.COMMODITY_CODE,
    ps.[DESCRIPTION],





    dj.USER_10,
    dj.USER_1 AS col_user_1,

    -- RWPart (rework-aware)
    RWPart = IIF(rwo.PART_ID = N'REWORK MFG', ei.PART_ID, rwo.PART_ID),
	Report_Part = COALESCE(ei.PART_ID, rwo.PART_ID),

    dj.CUSTOMER_PO_REF,

    -- Work order notes as text (unchanged)
    CONVERT(nvarchar(max), CONVERT(varbinary(max), wb.BITS)) AS WORK_ORDER_NOTES,

    dj.CUST_ORD_CREATEDATE,

    -- Material/Alloy and combined
    ISNULL(NULLIF(mat.Material, N''), N'_blank') AS PartMaterialType,
    ISNULL(NULLIF(alloy.Alloy,   N''), N'_blank') AS Alloy,
    CASE
        WHEN mat.Material IS NULL AND alloy.Alloy IS NULL THEN N'_blank'
        ELSE ISNULL(mat.Material, N'')
           + IIF(mat.Material IS NOT NULL, IIF(alloy.Alloy IS NOT NULL, N' ', N''), N'')
           + ISNULL(alloy.Alloy, N'')
    END AS MaterialType,

    dj.CO_AMOUNT,
    dj.UNIT_PRICE,
    dj.TOTAL_AMT_SHIPPED,
    dj.COL_AMOUNT
			-- update 4/27 for testing, udf fields must be explicitly typed
		, CASE
			WHEN EXISTS( SELECT 1 FROM #USER_DEF_FIELDS_W_48 UDF
				WHERE UDF.PROGRAM_ID = N'VMMFGWIN_OP'  
					AND UDF.ID = N'UDF-0000048' 
					AND UDF.[LABEL] IS NULL 
					AND UDF.BOOL_VAL = 1
					AND rwo.[TYPE] = UDF.[TYPE]  
					AND rwo.BASE_ID = UDF.base_id 
					AND rwo.LOT_ID = UDF.lot_ID 
					AND rwo.SUB_ID = UDF.sub_id
					AND rwo.SPLIT_ID = UDF.SPLIT_id
				) THEN CONVERT(INT, 1)
			ELSE CONVERT(INT, 0)
		END AS TimeLimit

	into Staging.dbo.WODS_Comp_test223
FROM ResolvedWO            AS rwo
LEFT JOIN dbo.WORKORDER_BINARY AS wb
    ON  wb.WORKORDER_BASE_ID  = rwo.BASE_ID
    AND wb.WORKORDER_LOT_ID   = rwo.LOT_ID
    AND wb.WORKORDER_SPLIT_ID = rwo.SPLIT_ID
    AND wb.WORKORDER_SUB_ID   = rwo.SUB_ID
    AND wb.WORKORDER_TYPE     = rwo.[TYPE]
LEFT JOIN DemandJoin       AS dj
    ON  dj.SUPPLY_BASE_ID   = rwo.BASE_ID
    AND dj.SUPPLY_LOT_ID    = rwo.LOT_ID
    AND dj.SUPPLY_SPLIT_ID  = rwo.SPLIT_ID
LEFT JOIN EndItem          AS ei
    ON  ei.[TYPE]    = rwo.[TYPE]
    AND ei.BASE_ID   = rwo.BASE_ID
    AND ei.LOT_ID    = rwo.LOT_ID
    AND ei.SPLIT_ID  = rwo.SPLIT_ID
    AND ei.SUB_ID    = N'0'
LEFT JOIN PartSite         AS ps   ON ps.PART_ID = rwo.PART_ID  AND ps.SITE_ID = N'SK01'
LEFT JOIN PartSite         AS eps  ON eps.PART_ID = ei.PART_ID  AND eps.SITE_ID = N'SK01'
LEFT JOIN MaterialUDF      AS mat  ON mat.PART_ID = rwo.PART_ID
LEFT JOIN AlloyUDF         AS alloy ON alloy.PART_ID = rwo.PART_ID

where 1=1
   and (rwo.BASE_ID = @base_id or @base_id is null)
order by
  [exp/flt] ASC
  ,DESIRED_WANT_DATE -- DUE DATE
  ;
SELECT * from Staging.dbo.WODS_Comp_test223
order by
  [exp/flt] ASC
  ,DESIRED_WANT_DATE -- DUE DATE
;



