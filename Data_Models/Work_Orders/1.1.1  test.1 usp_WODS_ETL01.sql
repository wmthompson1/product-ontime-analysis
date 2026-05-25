USE [LIVE]
GO

/****** Object:  StoredProcedure [dbo].[usp_WODS_ETL01]    Script Date: 12/15/2025 8:38:54 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



/* =============================================
-- Author:		Eric Shafer 
-- Create date: 5/25/2018
-- Description:	Data set for the Work Order Daily Status report.
-- Update: tt20181111 - Added AP1_BUYER_Michele aggregate for buyer MicheleC; Changed Sunni's aggregate from AP1_BUYER_Michele to AP1_BUYER_Sunni
-- Update: tt20190424 - added shop_resources_view fields - USER_2, USER_3, Supervisor's email_addr
-- Update: tt20190723 - added LTRIM(RTRIM(sr.USER_4))
-- Update: tt20190816 - updated new salesreps
-- update: vme 20190822 - updated work order desired_rls_date for legs (added case statement)
			updated purchase order desired_recv_date to include promise_ship_date  
			updated notes field to add customer user_1 for Boeing To OSP date (when planned work order is planned to go to outside processing.)
			updated col.user_10 to col.user_1 per request from Ann
-- update: vme/wt 20190822 - removed stored procedure GetReportSettings and incoporated into this stored procedure
			created temp tables with temp indexes to optimize user_def_fields table (Part 1)
-- update: vme/wt 20190912 - updated partmaterialtype to accommodate blanks in data
-- Update: tt20190925 - Changed AP1_BUYER_Michele aggregate for buyer AP1_BUYER_Danielle 
-- Update: tt20191120 - added ShopResource User fields
-- Update: vme 20200122 - updated linked server SQL-BI-1 to SQL-LAB-2 for resourceID_reportsettings
-- Update: wnt 20200424	- updated customer id logic for unlinked (make-to-stock) cust id
-- Update: wnt 20200427 - added temp table in order to explicitly type user def fields. (bug @ time limit field)
-- Update: wnt 20200615 - left joined a second work_order set pointed at end item (sub id 0)
			Customer ID derived from _all_ or _any_ buyer id for unlinked records. 
			Drop down for cust updated.
-- Update: wnt 20200626 - Null Handling for Wait Days (was causing filter problems)
-- UpDate: wnt 20200716 - alloy now appended to material type 
-- Update: wnt 20200817 - updated code defect 8/17/2020 wt cte_laborTickets was one-to-many causing dups
-- Update: wnt Code Base 2.1.0.2 - Work Order Less Tempdb
-- update: wnt 20201007 service ops
-- Update: tt20201203 - removed facility from Danielle's salesrepid aggregate
-- Update: tt20210305 - update for BUI-derived CustomerIDs
-- Update: tt20210427 - created new version; ADD OPERATION.USER_10 AS SETUP_INFO (NEW FIELD) (Ticket #522)
-- Update: tt20210430 - updated User_8 for Skyflex
-- Update: tt20210727 - update to add last closed operation date to last_clocked
-- Update: tt20210729 - updated CUSTOMER_ID FOR SPIMOR
*/

---CREATE PROCEDURE [dbo].[usp_WODS_ETL01] AS
-- *this version is run @ sql-lab-1

IF OBJECT_ID('tempdb..#WODS_Output')IS NOT NULL DROP TABLE #WODS_Output

SET NOCOUNT off;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

CREATE TABLE #WODS_Output(
	[BASE_ID] NVARCHAR(30) NOT NULL,
	[LOT_ID] NVARCHAR(3) NOT NULL,
	[SPLIT_ID] NVARCHAR(3) NOT NULL,
	[SUB_ID] NVARCHAR(3) NOT NULL,
	[TYPE] NCHAR(1) NOT NULL,
	[PART_ID] NVARCHAR(30) NULL,
	[WONUM] NVARCHAR(42) NULL,
	[DESIRED_QTY] DECIMAL(14,4) NULL,
	[STATUS] NCHAR(1) NOT NULL,
	[CUSTOMER_ORDER] NVARCHAR(15) NULL,
	[LINE_NO] SMALLINT NULL,
	[CUSTOMER_ID] NVARCHAR(15) NULL,
	[allocation_type] VARCHAR(8) NULL,
	[CurrentOperation] INT NULL,
	[StatusCurrOp] SMALLINT NULL,
	[PRINTED_DATE] DATETIME NULL,
	[DESIRED_RLS_DATE] DATETIME NULL,
	[CREATE_DATE] DATETIME NOT NULL,
	[remaining_operations] NVARCHAR(MAX) NOT NULL,
	[QTY_ON_HAND] DECIMAL(14,4) NOT NULL,
	[QTY_IN_DEMAND] DECIMAL(14,4) NOT NULL,
	[BUYER_USER_ID] NVARCHAR(20) NULL,
	[PLANNER_USER_ID] NVARCHAR(20) NULL,
	[COMMODITY_CODE] NVARCHAR(15) NULL,
	[DESCRIPTION] NVARCHAR(120) NULL,
	[DESIRED_WANT_DATE] DATETIME NULL,
	[EXP/FLT] NVARCHAR(254) NULL,
	[user_10] NVARCHAR(80) NULL,
	[col_user_1] NVARCHAR(80) NULL,
	[RWPart] NVARCHAR(30) NULL,
	[CUSTOMER_PO_REF] NVARCHAR(40) NULL,
	[WORK_ORDER_NOTES] NVARCHAR(MAX) NULL,
	[CUST_ORDER_NOTATION] NVARCHAR(MAX) NULL,
	[CUST_ORD_CREATEDATE] DATETIME NULL,
	[PartMaterialType] NVARCHAR(254) NOT NULL,
	[MaterialType] NVARCHAR(509) NOT NULL,
	[Alloy] NVARCHAR(254) NOT NULL,
	[CO_AMOUNT] DECIMAL(15,2) NULL,
	[UNIT_PRICE] DECIMAL(15,6) NULL,
	[TOTAL_AMT_SHIPPED] DECIMAL(15,2) NULL,
	[COL_AMOUNT] DECIMAL(15,2) NULL,
	[RESOURCE_ID_Raw] NVARCHAR(15) NULL,
	[OPERATION_TYPE] NVARCHAR(15) NULL,
	[StatusCurrOpType] NVARCHAR(15) NULL,
	[CURROPCHK] INT NULL,
	[RESOURCE_ID] NVARCHAR(15) NULL,
	[AubPriText] NVARCHAR(MAX) NULL,
	[AubTcText] NVARCHAR(MAX) NULL,
	[HasAubPri] INT NOT NULL,
	[HasAubTc] INT NOT NULL,
	[TimeLimit] INT NULL,
	[LAST_CLOCK_OUT] DATETIME NULL,
	[last_worked_seq] SMALLINT NULL,
	[last_clocked] NVARCHAR(81) NULL,
	[LATE] INT NOT NULL,
	[LATEP2] INT NOT NULL,
	[LATEP1] INT NOT NULL,
	[LATEP3] INT NOT NULL,
	[LATEBP1] INT NOT NULL,
	[WAIT_DAYS] INT NOT NULL,
	[EMPLOYEE_ID] NVARCHAR(15) NULL,
	[OPERATOR] NVARCHAR(61) NOT NULL,
	[USER_1] NVARCHAR(80) NULL,
	[LEAD_SUPERVISOR] NVARCHAR(111) NULL,
	[SupervisorName] NVARCHAR(80) NULL,
	[StatusCurrOpMsg] NVARCHAR(128) NULL,
	[tdesc] NVARCHAR(198) NOT NULL,
	[LABOR_TICKET_DESC] NVARCHAR(80) NULL,
	[BUYER] NVARCHAR(257) NOT NULL,
	[BUYERFILTER] NVARCHAR(255) NULL,
	[SALESREP_ID] NVARCHAR(255) NULL,
	[Account] NVARCHAR(5) NOT NULL,
	[Plant_ID] NVARCHAR(30) NOT NULL,
	[Tooling] INT NOT NULL,
	[IsAP1] INT NOT NULL,
	[IsAP2] INT NOT NULL,
	[IsAP3] INT NOT NULL,
	[IsBP1] INT NOT NULL,
	[IsUndetermined] INT NOT NULL,
	[IsNORGRU] INT NOT NULL,
	[IsTWMETA] INT NOT NULL,
	[IsAMTRIB] INT NOT NULL,
	[IsAUBMASK] INT NOT NULL,
	[IsAUBPrime] INT NOT NULL,
	[IsAUBSand] INT NOT NULL,
	[IsAUBsetup] INT NOT NULL,
	[IsAUBTC] INT NOT NULL,
	[IsAUBtakedown] INT NOT NULL,
	[IsAUBPartMark] INT NOT NULL,
	[IsAUBFinalInspection] INT NOT NULL,
	[IsAUBInspection] INT NOT NULL,
	[IsAUBPenetrant] INT NOT NULL,
	[IsAUBChemline] INT NOT NULL,
	[AP1_ETRAC] INT NOT NULL,
	[AP2_ETRAC] INT NOT NULL,
	[AP3_ETRAC] INT NOT NULL,
	[BP1_ETRAC] INT NOT NULL,
	[AP1_PDEXP] INT NOT NULL,
	[AP2_PDEXP] INT NOT NULL,
	[AP3_PDEXP] INT NOT NULL,
	[BP1_PDEXP] INT NOT NULL,
	[AP1_FLT] INT NOT NULL,
	[AP2_FLT] INT NOT NULL,
	[AP3_FLT] INT NOT NULL,
	[BP1_FLT] INT NOT NULL,
	[AP1_Buyer_Joe] INT NOT NULL,
	[AP1_Buyer_Rena] INT NOT NULL,
	[AP1_Buyer_Tiffany] INT NOT NULL,
	[AP1_Buyer_Sunni] INT NOT NULL,
	[AP1_Buyer_Danielle] INT NOT NULL,
	[AP1_Review] INT NOT NULL,
	[AP1_PlanningQueue] INT NOT NULL,
	[AP1_SkyFlex] INT NOT NULL,
	[ID] NVARCHAR(15) NULL,
	[DESIRED_RECV_DATE] DATETIME NULL,
	[SnapshotDate] DATETIME NOT NULL,
	[DEPARTMENT] NVARCHAR(80) NULL,
	[SUB_DEPARTMENT] NVARCHAR(80) NULL,
	[FACILITY] NVARCHAR(80) NULL,
	[REPT_DEPT] NVARCHAR(80) NULL,
	[PROCESS] NVARCHAR(80) NULL,
	[REPORT_GROUPING] NVARCHAR(80) NULL,
	[EMAIL_ADDR] NVARCHAR(80) NULL,
	[SETUP_INFO] NVARCHAR(80) NULL
) 

wods_query_begins:

IF OBJECT_ID('tempdb..#cte_wo') IS NOT NULL DROP TABLE #cte_wo
IF OBJECT_ID('tempdb..#temp1') IS NOT NULL DROP TABLE #temp1

DECLARE @ReportName NVARCHAR(255) = 'WODS'
	, @cols AS NVARCHAR(MAX)
	, @query AS NVARCHAR(MAX);

SET @cols = STUFF((SELECT DISTINCT ',' + QUOTENAME(c.Report_Section) 
	FROM [SQL-LAB-2].LIVESupplemental.dbo.ReportSettings_ResourceID c
	WHERE c.Report_Name = @ReportName
	FOR XML PATH(''), TYPE
	).value('.', 'NVARCHAR(MAX)'), 1, 1, '')
	
SET @query = 'SELECT Resource, ' + @cols + ' FROM
	(SELECT Resource
		, CAST(Include AS INT)Include
		, Report_Section
	FROM (SELECT [Resource_ID] AS Resource, [Report_Name], [Report_Section], [Reasoning], [Notes], [Include]
		FROM [SQL-LAB-2].LIVESupplemental.dbo.[ReportSettings_ResourceID] 
		) A
	WHERE A.Report_Name = ''' + @ReportName + '''
	) X
	PIVOT (MAX(Include)
	FOR Report_Section IN (' + @Cols + ')
	)P '
--PRINT @query
--SELECT @query

DECLARE @ReportSettings AS TABLE 
	(Resource NVARCHAR(30)
	, AP1_Review INT
	, [HasASSEMBLY] INT
	, HasAubPri INT
	, HasAubTc INT
	, [HasMasking] INT
	, [IsASSEMBLY] INT
	, IsAUBChemline INT
	, IsAUBFinalInspection INT
	, IsAUBInspection INT
	, IsAUBMASK INT
	, IsAUBPartMark INT
	, IsAUBPenetrant INT
	, IsAubPrime INT
	, IsAUBSand INT
	, IsAUBsetup INT
	, IsAUBtakedown INT
	, IsAUBTC INT
	, [IsMasking] INT
	, RESOURCE_ID_OpType INT
	, RESOURCE_ID_SERVICE INT
	)

INSERT INTO @ReportSettings EXECUTE(@query)
--SELECT * FROM @ReportSettings

IF OBJECT_ID('tempdb..#NOTATIONBYOWNER') IS NOT NULL DROP TABLE #NOTATIONBYOWNER
IF OBJECT_ID('tempdb..#WORK_ORDER') IS NOT NULL DROP TABLE #WORK_ORDER
IF OBJECT_ID('tempdb..#USER_DEF_FIELDS') IS NOT NULL DROP TABLE #USER_DEF_FIELDS
IF OBJECT_ID('tempdb..#USER_DEF_FIELDS_W_48') IS NOT NULL DROP TABLE #USER_DEF_FIELDS_W_48
IF OBJECT_ID('tempdb..#cte_wo') IS NOT NULL DROP TABLE #cte_wo

SELECT N.OWNER_ID
	, (SELECT CAST(CREATE_DATE AS NVARCHAR(12)) + N' - ' + CAST(CAST(NOTE AS VARBINARY(MAX)) AS NVARCHAR(MAX)) + N', ' + CHAR(10) + CHAR(13)
		FROM NOTATION N1
		WHERE N1.OWNER_ID = N.OWNER_ID
			AND N1.[TYPE] = N'CO'
		ORDER BY CREATE_DATE
		FOR XML PATH('')
	) AS NOTE
INTO #NOTATIONBYOWNER
FROM NOTATION N
WHERE N.[TYPE] = N'CO'
--AND OWNER_ID = '417967'
GROUP BY OWNER_ID

CREATE CLUSTERED INDEX CINOTATE ON #NOTATIONBYOWNER (OWNER_ID)

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

INSERT INTO #USER_DEF_FIELDS_W_48
	([TYPE] 		
		, BASE_ID 	
		, LOT_ID 	
		, SUB_ID 	
		, SPLIT_ID 	
		, [PROGRAM_ID]  
		, [ID]  
		, [LABEL]  
		, [BOOL_VAL]  
	)
	SELECT [TYPE] = SUBSTRING(ud.DOCUMENT_ID, 0, CHARINDEX(N'~',ud.DOCUMENT_ID))
		, BASE_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) - CHARINDEX(N'~', ud.DOCUMENT_ID) - 1) 
		, LOT_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) + 1) + 1, 1)
		, SUB_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID) + 1) + 1, 1) 
		, SPLIT_ID = SUBSTRING(ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~', ud.DOCUMENT_ID, CHARINDEX(N'~',ud.DOCUMENT_ID, CHARINDEX(N'~',ud.DOCUMENT_ID) + 1) + 1) + 1) + 1, 1) 
		, ud.PROGRAM_ID
		, ud.ID
		, ud.[LABEL]
		, ud.BOOL_VAL
	FROM USER_DEF_FIELDS ud
	WHERE ud.PROGRAM_ID = N'VMMFGWIN_OP'
		AND ud.ID = N'UDF-0000048' 
		AND ud.[LABEL] IS NULL 
		AND ud.BOOL_VAL = 1

CREATE NONCLUSTERED INDEX N2CIDX_UDF_w_48 ON #USER_DEF_FIELDS_W_48 	
	(BASE_ID
		, LOT_ID
		, SUB_ID
		, SPLIT_ID
		, [TYPE]
	)

CREATE NONCLUSTERED INDEX NCIDX_UDF_w_48 ON #USER_DEF_FIELDS_W_48 (PROGRAM_ID) 
INCLUDE (ID
		, [LABEL]
		, BOOL_VAL
	)

SELECT wo.BASE_ID
	, wo.LOT_ID
	, wo.SPLIT_ID
	, wo.SUB_ID
	, wo.[TYPE]
	, CASE 
		WHEN wo.PART_ID = N'REWORK MFG' THEN 
			(SELECT PART_ID 
			FROM WORK_ORDER w 
			WHERE w.[TYPE] = wo.[TYPE] 
			AND w.BASE_ID = wo.BASE_ID 
			AND w.LOT_ID = wo.LOT_ID 
			AND w.SPLIT_ID = wo.SPLIT_ID 
			AND w.SUB_ID = N'0'  
			AND w.PART_ID <> N'REWORK MFG'
			)
		ELSE wo.PART_ID 
	END PART_ID
	, dbo.sfnWONUMFormat(wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID) AS WONUM
	, wo.DESIRED_QTY
	, wo.[STATUS]
	, col.CUST_ORDER_ID AS CUSTOMER_ORDER
	, col.LINE_NO

--Customer ID calc;
--1st Customer ID for linked
--2nd Parse the Buyer ID – unlinked  **
--3rd Rework (FIN) will use the end item record (sub id 0) to cross reference and resolve.
--> tt20210305: update BUI-derived CustomerIDs for specific values
--> original code:
--	, CUSTOMER_ID2 = IIF(
--	(CASE WHEN (dsl.DEMAND_BASE_ID IS NULL AND dsl.DEMAND_SEQ_NO IS NULL AND dsl.DEMAND_TYPE IS NULL) THEN 'Unlinked' END) = 'unlinked' AND NULLIF(LTRIM(RTRIM(CO.CUSTOMER_ID)),'') IS NULL 
--		, IIF(ISNUMERIC(SUBSTRING(P.BUYER_USER_ID, 4, 1) ) = 1
--		, 'BOEPOP'
--		, SUBSTRING(P.BUYER_USER_ID, 4, 6)
--	), CO.customer_ID
--	)
	, CUSTOMER_ID2 = IIF(
		dsl.DEMAND_BASE_ID IS NULL AND dsl.DEMAND_SEQ_NO IS NULL AND dsl.DEMAND_TYPE IS NULL    --> UNLINKED
			AND NULLIF(LTRIM(RTRIM(CO.CUSTOMER_ID)),'') IS NULL  --> NO CUSTOMERID
			, CASE
				WHEN ISNUMERIC(SUBSTRING(P.BUYER_USER_ID, 4, 1)) = 1 THEN 'BOEPOP'
				WHEN SUBSTRING(P.BUYER_USER_ID, 4, 3) = 'DEF' THEN 'BOEDEF'
--> tt20210729: added for SPIMOR
				WHEN SUBSTRING(P.BUYER_USER_ID, 4, 6) = 'SPIMOR' THEN 'SPIMOR'
				WHEN SUBSTRING(P.BUYER_USER_ID, 4, 3) = 'SPI' THEN 'SPIAER'
				WHEN SUBSTRING(P.BUYER_USER_ID, 4, 4) = 'CMPF' THEN P.PLANNER_USER_ID
				ELSE SUBSTRING(P.BUYER_USER_ID, 4, 6)
			END
			, CO.CUSTOMER_ID
	)

--> ORIGINAL CODE:
--, CUSTOMER_ID = IIF(
--	(CASE WHEN (dsl.DEMAND_BASE_ID IS NULL AND dsl.DEMAND_SEQ_NO IS NULL AND dsl.DEMAND_TYPE IS NULL ) THEN 'UNLINKED' END) = 'UNLINKED' AND NULLIF(LTRIM(RTRIM(CO.CUSTOMER_ID)),'') IS NULL
--		, IIF(ISNUMERIC(SUBSTRING(EndItemPart.buyer_user_id,4,1) ) = 1
--		,'BOEPOP'
--	, SUBSTRING(EndItemPart.buyer_user_id, 4, 6)
--		), CO.customer_ID
--	)
	, CUSTOMER_ID = IIF(
		dsl.DEMAND_BASE_ID IS NULL AND dsl.DEMAND_SEQ_NO IS NULL AND dsl.DEMAND_TYPE IS NULL    --> UNLINKED
			AND NULLIF(LTRIM(RTRIM(CO.CUSTOMER_ID)),'') IS NULL  --> NO CUSTOMERID
			, CASE
				WHEN ISNUMERIC(SUBSTRING(EndItemPart.buyer_user_id, 4, 1)) = 1 THEN 'BOEPOP'
				WHEN SUBSTRING(EndItemPart.buyer_user_id, 4, 3) = 'DEF' THEN 'BOEDEF'
--> tt20210729: added for SPIMOR
				WHEN SUBSTRING(P.BUYER_USER_ID, 4, 6) = 'SPIMOR' THEN 'SPIMOR'
				WHEN SUBSTRING(EndItemPart.buyer_user_id, 4, 3) = 'SPI' THEN 'SPIAER'
				WHEN SUBSTRING(EndItemPart.buyer_user_id, 4, 4) = 'CMPF' THEN EndItemPart.PLANNER_USER_ID
				ELSE SUBSTRING(EndItemPart.buyer_user_id, 4, 6)
			END
			, CO.CUSTOMER_ID
	)
	, EndItemPart.part_id EndItem_Part_id
	, EndItemPart.BUYER_USER_ID EndItem_Buyer_User_ID
	, Allocation_Type = CASE WHEN (dsl.DEMAND_BASE_ID IS NULL AND dsl.DEMAND_SEQ_NO IS NULL AND dsl.DEMAND_TYPE IS NULL) THEN 'Unlinked' END
	, SUBSTRING(P.BUYER_USER_ID, 4, 1) buyer_ptr
	, dbo.sfn_current_operation(wo.[TYPE], wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID) AS CurrentOperation
	, ISNULL(dbo.sfn_getlastopcompleted(wo.[TYPE], wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID), dbo.ufn_GetFirstOperation(wo.BASE_ID, wo.LOT_ID, wo.SUB_ID, wo.SPLIT_ID, wo.[TYPE])) AS StatusCurrOp
	, wo.PRINTED_DATE
	, CASE   -- added 8/22/2019 VME
		WHEN WO.DESIRED_RLS_DATE IS NULL THEN (SELECT W.DESIRED_RLS_DATE
			FROM WORK_ORDER W
			WHERE W.[TYPE] = WO.[TYPE]
				AND W.BASE_ID = WO.BASE_ID
				AND W.LOT_ID = WO.LOT_ID
				AND W.SPLIT_ID = WO.SPLIT_ID
				AND W.SUB_ID = N'0'
		)
		ELSE WO.DESIRED_RLS_DATE
	END DESIRED_RLS_DATE
	, ISNULL(co.CREATE_DATE, wo.CREATE_DATE) AS CREATE_DATE
	, ISNULL(dbo.sfn_remaining_operations(wo.[TYPE], wo.BASE_ID, wo.LOT_ID, wo.SPLIT_ID, wo.SUB_ID), N'No Remaining Operations') remaining_operations
	, p.QTY_ON_HAND QTY_ON_HAND
	, p.QTY_IN_DEMAND QTY_IN_DEMAND
	, P.BUYER_USER_ID BUYER_USER_ID
	, RTRIM(p.PLANNER_USER_ID) PLANNER_USER_ID
	, p.COMMODITY_CODE
	, p.[DESCRIPTION]
	, ISNULL(wo.DESIRED_WANT_DATE
	, (SELECT MIN(DESIRED_WANT_DATE) FROM WORK_ORDER w WHERE wo.[TYPE] = w.[TYPE] AND wo.BASE_ID = w.BASE_ID AND wo.LOT_ID = w.LOT_ID AND wo.SPLIT_ID = w.SPLIT_ID AND wo.SUB_ID <> w.SUB_ID)) AS DESIRED_WANT_DATE
	, (SELECT TOP 1 STRING_VAL 
		FROM USER_DEF_FIELDS ud
		WHERE ud.PROGRAM_ID = N'VMMFGWIN_WO'
			AND ud.ID = N'UDF-0000070' 
			AND ISNULL(ud.LABEL, '') = ''
			AND wo.[TYPE] + N'~' + wo.BASE_ID + N'~' + N'0' + N'~' + wo.LOT_ID + N'~' + wo.SPLIT_ID = ud.DOCUMENT_ID
	) AS [EXP/FLT]
	, col.user_10 
	, col.USER_1 AS col_user_1
	, CASE 
		WHEN wo.PART_ID = N'REWORK MFG' THEN (SELECT PART_ID 
			FROM WORK_ORDER w 
			WHERE w.[TYPE] = wo.[TYPE] 
				AND w.BASE_ID = wo.BASE_ID 
				AND w.LOT_ID = wo.LOT_ID 
				AND w.SPLIT_ID = wo.SPLIT_ID 
				AND w.SUB_ID = '0'
				AND w.PART_ID <> N'REWORK MFG'
			)
		ELSE wo.PART_ID 
	END AS RWPart
	, co.CUSTOMER_PO_REF
	, CONVERT(NVARCHAR(MAX), CONVERT(VARBINARY(MAX), wb.BITS)) AS WORK_ORDER_NOTES
	, n.NOTE AS CUST_ORDER_NOTATION
	, co.CREATE_DATE AS CUST_ORD_CREATEDATE
	, ISNULL(nullif(material.material, ''), '_blank') AS PartMaterialType
	, ISNULL(NULLIF(alloy.alloy, ''), '_blank') AS Alloy
	, CASE 
		WHEN Material.Material IS NULL and alloy.alloy IS NULL then'_blank'
		ELSE ISNULL(Material.Material, '') + IIF(Material.Material IS NOT NULL, IIF(alloy.alloy IS NOT NULL, ' ', ''), '') + ISNULL(alloy.Alloy, '') 
	END AS MaterialType
	, CO.TOTAL_AMT_ORDERED AS CO_AMOUNT
	, COL.UNIT_PRICE
	, COL.TOTAL_AMT_SHIPPED
	, COL.TOTAL_AMT_ORDERED AS COL_AMOUNT
INTO #cte_wo
FROM WORK_ORDER wo2
JOIN WORK_ORDER wo
	ON wo2.[TYPE] = wo.[TYPE]
	AND wo2.[BASE_ID] = wo.[BASE_ID]
	AND wo2.[LOT_ID] = wo.[LOT_ID]
	AND wo2.[SPLIT_ID] = wo.[SPLIT_ID]
	AND wo2.[SUB_ID] = wo.[SUB_ID]
LEFT JOIN WORK_ORDER EndItem
	ON EndItem.[TYPE] = wo.[TYPE]
	AND EndItem.[BASE_ID] = wo.[BASE_ID]
	AND EndItem.[LOT_ID] = wo.[LOT_ID]
	AND EndItem.[SPLIT_ID] = wo.[SPLIT_ID]
	AND EndItem.[SUB_ID] = '0'
LEFT JOIN WORKORDER_BINARY wb
	ON wb.WORKORDER_BASE_ID = wo.BASE_ID
	AND wb.WORKORDER_LOT_ID = wo.LOT_ID
	AND wb.WORKORDER_SPLIT_ID = wo.SPLIT_ID
	AND wb.WORKORDER_SUB_ID = wo.SUB_ID
	AND wb.WORKORDER_TYPE = wo.[TYPE] 
LEFT JOIN DEMAND_SUPPLY_LINK dsl
	ON dsl.SUPPLY_BASE_ID = wo.BASE_ID
	AND dsl.SUPPLY_LOT_ID = wo.LOT_ID
	AND dsl.SUPPLY_SPLIT_ID = wo.SPLIT_ID
--AND dsl.SUPPLY_SUB_ID = wo.SUB_ID  --MUST OMIT FOR LEGS AND REWORKS
LEFT JOIN CUST_ORDER_LINE col
	ON col.CUST_ORDER_ID = dsl.DEMAND_BASE_ID
	AND col.LINE_NO = dsl.DEMAND_SEQ_NO
	AND dsl.DEMAND_TYPE = N'CO'
LEFT JOIN CUSTOMER_ORDER co
	ON co.ID = col.CUST_ORDER_ID
LEFT JOIN #NOTATIONBYOWNER n
	ON n.OWNER_ID = co.ID
JOIN PART_SITE_VIEW p 
	ON p.PART_ID = wo.PART_ID
	AND p.SITE_ID = N'SK01'
left JOIN PART_SITE_VIEW EndItemPart
	ON EndItemPart.PART_ID = EndItem.PART_ID
	AND EndItemPart.SITE_ID = N'SK01'
	AND EndItemPart.PART_ID <> 'REWORK MFG'
			outer APPLY (SELECT top 1 pud2.DOCUMENT_ID
				, pud2.id
				, pud2.LABEL
				, NULLIF(pud2.STRING_VAL,'') AS Material
				, pud2.PROGRAM_ID
				, p.id part_id
			from USER_DEF_FIELDS pUD2
			join part p 
			on pud2.DOCUMENT_ID = p.id
			where pUD2.ID in ('UDF-0000035') -- material
			AND pUD2.PROGRAM_ID = 'VMPRTMNT'
			and pUD2.DOCUMENT_ID IS NOT NULL
			AND wo.PART_ID = pUD2.DOCUMENT_ID
			) Material

		outer APPLY (SELECT top 1 pud3.document_id
			, pud3.id
			, pud3.label
			, nullif(pud3.string_val,'') AS alloy
			, pud3.program_id
			, p3.id part_id
		from user_def_fields pud3
		join part p3 
		on pud3.document_id = p3.id
		where pUD3.ID in ('UDF-0000036')  -- prtMnt Alloy
		AND pUD3.PROGRAM_ID = 'VMPRTMNT'
		and pUD3.DOCUMENT_ID IS NOT NULL
		AND wo.PART_ID = pUD3.DOCUMENT_ID
		) alloy

LEFT JOIN LIVESupplemental.dbo.SK_CUST_SPECIFIC_PARTS cp
	ON cp.PART_ID = p.PART_ID
WHERE wo.[STATUS] IN (N'R', N'F', N'U')
	AND wo.[TYPE] = N'W'


CREATE CLUSTERED INDEX ix_tempctewo ON #cte_wo(TYPE ASC, BASE_ID ASC, LOT_ID ASC, SPLIT_ID ASC, SUB_ID ASC);
CREATE NONCLUSTERED INDEX ixtempctewo_CurOp ON #cte_wo(CurrentOperation ASC);
CREATE NONCLUSTERED INDEX ixtempctewo_StatusCurOp ON #cte_wo(StatusCurrOp ASC);

; WITH cte_LastClockOut AS
(SELECT A.WORKORDER_BASE_ID
	, A.WORKORDER_LOT_ID
	, A.WORKORDER_SPLIT_ID
	, A.WORKORDER_SUB_ID
	, A.WORKORDER_TYPE
	, A.LAST_CLOCK_OUT
	, MAX(OPERATION_SEQ_NO) AS LAST_OPERATION
FROM (SELECT LT.WORKORDER_BASE_ID
		, LT.WORKORDER_LOT_ID
		, LT.WORKORDER_SPLIT_ID
		, LT.WORKORDER_SUB_ID
		, LT.WORKORDER_TYPE
		, MAX(LT.CLOCK_OUT) AS LAST_CLOCK_OUT
	FROM LABOR_TICKET LT
	WHERE EXISTS (SELECT 1 FROM #cte_wo WO
		WHERE LT.WORKORDER_BASE_ID = WO.BASE_ID
		AND LT.WORKORDER_LOT_ID = WO.LOT_ID
		AND LT.WORKORDER_SPLIT_ID = WO.SPLIT_ID
		AND LT.WORKORDER_SUB_ID = WO.SUB_ID
		AND LT.WORKORDER_TYPE = WO.[TYPE]
		)
	GROUP BY LT.WORKORDER_BASE_ID
		, LT.WORKORDER_LOT_ID
		, LT.WORKORDER_SPLIT_ID
		, LT.WORKORDER_SUB_ID
		, LT.WORKORDER_TYPE
	) A
JOIN LABOR_TICKET LT
	ON A.WORKORDER_BASE_ID = LT.WORKORDER_BASE_ID
	AND A.WORKORDER_LOT_ID = LT.WORKORDER_LOT_ID
	AND A.WORKORDER_SPLIT_ID = LT.WORKORDER_SPLIT_ID
	AND A.WORKORDER_SUB_ID = LT.WORKORDER_SUB_ID
	AND A.WORKORDER_TYPE = LT.WORKORDER_TYPE
	AND A.LAST_CLOCK_OUT = LT.CLOCK_OUT
GROUP BY A.WORKORDER_BASE_ID
	, A.WORKORDER_LOT_ID
	, A.WORKORDER_SPLIT_ID
	, A.WORKORDER_SUB_ID
	, A.WORKORDER_TYPE
	, A.LAST_CLOCK_OUT
)

, cte_labortickets AS
(SELECT x.*
FROM (SELECT lt.* 
	, a.last_clock_out
	, a.last_operation
	, rn = ROW_NUMBER() OVER (PARTITION BY lt.workorder_type
		, lt.workorder_base_id
		, lt.workorder_lot_id
		, lt.workorder_split_id
		, lt.workorder_sub_id
		, lt.operation_seq_no
		, lt.clock_out
		ORDER BY lt.transaction_id DESC
		)
	FROM labor_ticket lt (nolock)
	JOIN cte_lastclockout a 
		ON a.workorder_base_id = lt.workorder_base_id
		AND a.workorder_lot_id = lt.workorder_lot_id
		AND a.workorder_split_id = lt.workorder_split_id
		AND a.workorder_sub_id = lt.workorder_sub_id
		AND a.workorder_type = lt.workorder_type
		AND a.last_operation = lt.operation_seq_no
		AND a.last_clock_out = lt.clock_out
	) X
WHERE (1=1)
	AND x.rn = 1
)

--> TT20210727: add last closed date
, CTE_LASTOPCLOSED AS
(SELECT X.WORKORDER_BASE_ID
	, X.WORKORDER_LOT_ID
	, X.WORKORDER_SPLIT_ID
	, X.WORKORDER_SUB_ID
	, X.WORKORDER_TYPE
	, CASE
		WHEN WO.[STATUS] = 'F' THEN NULL
		ELSE X.LAST_CLOSED
	END AS LAST_CLOSED
	, MAX(O.SEQUENCE_NO) AS LAST_OPERATION
FROM (SELECT O.WORKORDER_BASE_ID
		, O.WORKORDER_LOT_ID
		, O.WORKORDER_SPLIT_ID
		, O.WORKORDER_SUB_ID
		, O.WORKORDER_TYPE
		, MAX(O.CLOSE_DATE) AS LAST_CLOSED
	FROM OPERATION O
	WHERE EXISTS (SELECT 1 FROM #cte_wo WO
		WHERE O.WORKORDER_BASE_ID = WO.BASE_ID
		AND O.WORKORDER_LOT_ID = WO.LOT_ID
		AND O.WORKORDER_SPLIT_ID = WO.SPLIT_ID
		AND O.WORKORDER_SUB_ID = WO.SUB_ID
		AND O.WORKORDER_TYPE = WO.[TYPE]
		)
	GROUP BY O.WORKORDER_BASE_ID
		, O.WORKORDER_LOT_ID
		, O.WORKORDER_SPLIT_ID
		, O.WORKORDER_SUB_ID
		, O.WORKORDER_TYPE
	) X
JOIN OPERATION O
	ON X.WORKORDER_BASE_ID = O.WORKORDER_BASE_ID
	AND X.WORKORDER_LOT_ID = O.WORKORDER_LOT_ID
	AND X.WORKORDER_SPLIT_ID = O.WORKORDER_SPLIT_ID
	AND X.WORKORDER_SUB_ID = O.WORKORDER_SUB_ID
	AND X.WORKORDER_TYPE = O.WORKORDER_TYPE
	AND X.LAST_CLOSED = O.CLOSE_DATE
JOIN WORK_ORDER WO
	ON X.WORKORDER_BASE_ID = WO.BASE_ID
	AND X.WORKORDER_LOT_ID = WO.LOT_ID
	AND X.WORKORDER_SPLIT_ID = WO.SPLIT_ID
	AND X.WORKORDER_SUB_ID = WO.SUB_ID
	AND X.WORKORDER_TYPE = WO.[TYPE]
GROUP BY X.WORKORDER_BASE_ID
	, X.WORKORDER_LOT_ID
	, X.WORKORDER_SPLIT_ID
	, X.WORKORDER_SUB_ID
	, X.WORKORDER_TYPE
	, WO.[STATUS]
	, X.LAST_CLOSED
)
--SELECT * FROM CTE_LASTOPCLOSED --WHERE WORKORDER_BASE_ID = '1657144'

, cte_currentoperation AS 
(SELECT w.*
	, ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID) RESOURCE_ID_Raw
	, o.OPERATION_TYPE
	, o2.OPERATION_TYPE AS StatusCurrOpType
	, w.CurrentOperation AS CURROPCHK
	, CASE 
		WHEN EXISTS(SELECT 1 FROM @ReportSettings s
			WHERE s.[Resource] = ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID)
				AND ISNULL(s.RESOURCE_ID_OpType, -1) <> - 1
			) THEN ISNULL(o.OPERATION_TYPE, o2.OPERATION_TYPE) 
		WHEN EXISTS(SELECT 1 FROM @ReportSettings s
			WHERE s.[Resource] = ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID)
				AND ISNULL(s.RESOURCE_ID_SERVICE, -1) <> -1
			) THEN o.VENDOR_ID
		ELSE ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID) 
	END AS RESOURCE_ID
	, CONVERT(NVARCHAR(MAX),CONVERT(VARBINARY(MAX),ob.BITS)) AS AubPriText
	, CONVERT(NVARCHAR(MAX),CONVERT(VARBINARY(MAX),otb.BITS)) AS AubTcText
	, CASE 
		WHEN ob.BITS IS NOT NULL OR EXISTS(SELECT 1 FROM @ReportSettings s 
			WHERE ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID) = s.[Resource] 
				AND ISNULL(s.HasAubPri, -1) <> -1) THEN 1 
		ELSE 0 
	END AS HasAubPri
	, CASE 
		WHEN otb.BITS IS NOT NULL OR EXISTS(SELECT 1 FROM @ReportSettings s 
			WHERE ISNULL(o.RESOURCE_ID, o2.RESOURCE_ID) = s.[Resource] 
				AND ISNULL(s.HasAubTc, -1) <> -1) THEN 1 
		ELSE 0 
	END AS HasAubTc

-- update 4/27 for testing, udf fields must be explicitly typed
	, CASE
		WHEN EXISTS(SELECT 1 FROM #USER_DEF_FIELDS_W_48 UDF
			WHERE UDF.PROGRAM_ID = N'VMMFGWIN_OP'  
				AND UDF.ID = N'UDF-0000048' 
				AND UDF.[LABEL] IS NULL 
				AND UDF.BOOL_VAL = 1
				AND W.[TYPE] = UDF.[TYPE]  
				AND W.BASE_ID = UDF.base_id 
				AND W.LOT_ID = UDF.lot_ID 
				AND W.SUB_ID = UDF.sub_id
				AND W.SPLIT_ID = UDF.SPLIT_id
			) THEN CONVERT(INT, 1)
		ELSE CONVERT(INT, 0)
	END AS TimeLimit
--> tt20210427: new field request from Ann (Ticket #522)
	, O.USER_10 AS SETUP_INFO
FROM #cte_wo w 
LEFT JOIN OPERATION o --LAST OP COMPLETE BASED ON STATUS C OR LTICKETS
	ON o.WORKORDER_BASE_ID = w.BASE_ID
	AND o.WORKORDER_LOT_ID = w.LOT_ID
	AND o.WORKORDER_SPLIT_ID = w.SPLIT_ID
	AND o.WORKORDER_SUB_ID = w.SUB_ID
	AND o.WORKORDER_TYPE = w.[TYPE] 
	AND o.SEQUENCE_NO = w.CurrentOperation
LEFT JOIN OPERATION o2 -- BASED ON LAST OP WITH STATUS C OR IF NONE, FIRST OP
	ON o2.WORKORDER_BASE_ID = w.BASE_ID
	AND o2.WORKORDER_LOT_ID = w.LOT_ID
	AND o2.WORKORDER_SPLIT_ID = w.SPLIT_ID
	AND o2.WORKORDER_SUB_ID = w.SUB_ID
	AND o2.WORKORDER_TYPE = w.[TYPE]
	AND o2.SEQUENCE_NO = w.StatusCurrOp
LEFT JOIN (SELECT o.WORKORDER_BASE_ID
		, o.WORKORDER_LOT_ID
		, o.WORKORDER_SPLIT_ID
		, o.WORKORDER_SUB_ID
		, o.WORKORDER_TYPE
		, o.SEQUENCE_NO
		, o.RESOURCE_ID
	FROM OPERATION O
	JOIN (SELECT o.WORKORDER_BASE_ID
			, o.WORKORDER_LOT_ID
			, o.WORKORDER_SPLIT_ID
			, o.WORKORDER_SUB_ID
			, o.WORKORDER_TYPE
			, MIN(SEQUENCE_NO) minAubPriSequence
		FROM OPERATION o
		WHERE EXISTS(SELECT 1 FROM #cte_wo w
			WHERE w.BASE_ID = o.WORKORDER_BASE_ID
				AND w.LOT_ID = o.WORKORDER_LOT_ID
				AND w.SPLIT_ID = o.WORKORDER_SPLIT_ID
				AND w.SUB_ID = o.WORKORDER_SUB_ID
				AND w.[TYPE] = o.WORKORDER_TYPE
				AND o.SEQUENCE_NO >= w.CurrentOperation
				)
			AND EXISTS(SELECT 1 FROM @ReportSettings s
				WHERE o.RESOURCE_ID = s.[Resource]
					AND ISNULL(s.HasAubTc, s.HasAubPri) IS NOT NULL
					)
			GROUP BY o.WORKORDER_BASE_ID
				, o.WORKORDER_LOT_ID
				, o.WORKORDER_SPLIT_ID
				, o.WORKORDER_SUB_ID
				, o.WORKORDER_TYPE
		) a
		ON a.WORKORDER_BASE_ID = o.WORKORDER_BASE_ID
		AND a.WORKORDER_LOT_ID = o.WORKORDER_LOT_ID
		AND a.WORKORDER_SUB_ID = o.WORKORDER_SUB_ID
		AND a.WORKORDER_SPLIT_ID = o.WORKORDER_SPLIT_ID
		AND a.WORKORDER_TYPE = o.WORKORDER_TYPE
		AND a.minAubPriSequence = o.SEQUENCE_NO
	) op
	ON op.WORKORDER_BASE_ID = w.BASE_ID
	AND op.WORKORDER_LOT_ID = w.LOT_ID
	AND op.WORKORDER_SPLIT_ID = w.SPLIT_ID
	AND op.WORKORDER_SUB_ID = w.SUB_ID
	AND op.WORKORDER_TYPE = w.[TYPE]
LEFT JOIN OPERATION_BINARY ob
	ON ob.WORKORDER_BASE_ID = op.WORKORDER_BASE_ID
	AND ob.WORKORDER_LOT_ID = op.WORKORDER_LOT_ID
	AND ob.WORKORDER_SPLIT_ID = op.WORKORDER_SPLIT_ID
	AND ob.WORKORDER_SUB_ID = op.WORKORDER_SUB_ID
	AND ob.WORKORDER_TYPE = op.WORKORDER_TYPE
	AND ob.SEQUENCE_NO = op.SEQUENCE_NO
	AND EXISTS(SELECT 1 FROM @ReportSettings s
		WHERE s.[Resource] = op.RESOURCE_ID
			AND ISNULL(s.HasAubPri, -1) <> -1
		)
LEFT JOIN OPERATION_BINARY otb
	ON otb.WORKORDER_BASE_ID = op.WORKORDER_BASE_ID
	AND otb.WORKORDER_LOT_ID = op.WORKORDER_LOT_ID
	AND otb.WORKORDER_SPLIT_ID = op.WORKORDER_SPLIT_ID
	AND otb.WORKORDER_SUB_ID = op.WORKORDER_SUB_ID
	AND otb.WORKORDER_TYPE = op.WORKORDER_TYPE
	AND otb.SEQUENCE_NO = op.SEQUENCE_NO
	AND EXISTS(SELECT 1 FROM @ReportSettings s
		WHERE op.RESOURCE_ID = s.[Resource]
			AND ISNULL(s.HasAubTc, -1) <> -1
		)
)
--SELECT * FROM cte_currentoperation

SELECT w.BASE_ID
	, w.LOT_ID
	, w.SPLIT_ID
	, w.SUB_ID
	, w.[TYPE]
	, w.PART_ID
	, w.WONUM
	, w.DESIRED_QTY
	, w.[STATUS]
	, w.CUSTOMER_ORDER
	, w.LINE_NO
	, CUSTOMER_ID = COALESCE(CUSTOMER_ID2, CUSTOMER_ID)
	, w.allocation_type
	, w.CurrentOperation
	, w.StatusCurrOp
	, w.PRINTED_DATE
	, w.DESIRED_RLS_DATE
	, w.CREATE_DATE
	, w.remaining_operations
	, w.QTY_ON_HAND
	, w.QTY_IN_DEMAND
	, w.BUYER_USER_ID
	, w.PLANNER_USER_ID
	, w.COMMODITY_CODE
	, w.[DESCRIPTION]
	, w.DESIRED_WANT_DATE
	, w.[EXP/FLT]
	, w.user_10
	, w.col_user_1
	, w.RWPart
	, w.CUSTOMER_PO_REF
	, w.WORK_ORDER_NOTES
	, w.CUST_ORDER_NOTATION
	, w.CUST_ORD_CREATEDATE
	-- wt 20200716  -- the new field in rendering alloy concat materieal is MaterialType
	, w.PartMaterialType AS PartMaterialType  -- old used for filter by material type
	-- wt 20200716  -- the old field is still used for filter by materialType
	, w.MaterialType AS MaterialType -- new 
	, w.Alloy
	, w.CO_AMOUNT
	, w.UNIT_PRICE
	, w.TOTAL_AMT_SHIPPED
	, w.COL_AMOUNT
	, w.RESOURCE_ID_Raw
	, w.OPERATION_TYPE
	, w.StatusCurrOpType
	, w.CURROPCHK
	, w.RESOURCE_ID
	, w.AubPriText
	, w.AubTcText
	, w.HasAubPri
	, w.HasAubTc
	, w.TimeLimit
	, l.LAST_CLOCK_OUT 
	, l.LAST_OPERATION AS last_worked_seq
--> TT20210727: add last closed date
	--, CONVERT(NVARCHAR(50), COALESCE(l.LAST_CLOCK_OUT, w.PRINTED_DATE, w.DESIRED_RLS_DATE), 1)  
	--	+ ' ' + CONVERT(NVARCHAR,CONVERT(TIME, COALESCE(l.LAST_CLOCK_OUT, w.PRINTED_DATE, w.DESIRED_RLS_DATE)), 0)
	--	as last_clocked
	, LO.LAST_CLOSED
	, CONVERT(NVARCHAR(50), COALESCE(l.LAST_CLOCK_OUT, LO.LAST_CLOSED, w.PRINTED_DATE, w.DESIRED_RLS_DATE), 1)  
		+ ' ' + CONVERT(NVARCHAR,CONVERT(TIME, COALESCE(l.LAST_CLOCK_OUT, LO.LAST_CLOSED, w.PRINTED_DATE, w.DESIRED_RLS_DATE)), 0)
		as last_clocked
	, CASE WHEN DATEDIFF(dd, w.DESIRED_WANT_DATE, GETDATE() ) > 2 THEN 1 ELSE 0 END AS LATE
	, CASE WHEN DATEDIFF(dd, w.DESIRED_WANT_DATE, GETDATE() ) > 4 AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP2' THEN 1 ELSE 0 END AS LATEP2
	, CASE WHEN DATEDIFF(dd, w.DESIRED_WANT_DATE, GETDATE() ) > 0 AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' THEN 1 ELSE 0 END AS LATEP1
	, CASE WHEN DATEDIFF(dd, w.DESIRED_WANT_DATE, GETDATE() ) > 2 AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP3' THEN 1 ELSE 0 END AS LATEP3
	, CASE WHEN DATEDIFF(dd, w.DESIRED_WANT_DATE, GETDATE() ) > 2 AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'BP1' THEN 1 ELSE 0 END AS LATEBP1
--> TT20210727: add last closed date
--	, ISNULL(DATEDIFF(dd, COALESCE(l.LAST_CLOCK_OUT, w.PRINTED_DATE, w.DESIRED_RLS_DATE), GETDATE()), 0) WAIT_DAYS
	, ISNULL(DATEDIFF(dd, COALESCE(L.LAST_CLOCK_OUT, LO.LAST_CLOSED, W.PRINTED_DATE, W.DESIRED_RLS_DATE), GETDATE()), 0) WAIT_DAYS
	, l.EMPLOYEE_ID
	, ISNULL(e.FIRST_NAME, '') + ' ' + ISNULL(e.LAST_NAME, '') OPERATOR
	, sr.USER_1
	, ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), '') + '-' + LTRIM(RTRIM(sr.USER_4)) AS LEAD_SUPERVISOR
	, RTRIM(ISNULL(LTRIM(RTRIM(sr.USER_4)), '_blank')) AS SupervisorName
	, COALESCE(CAST(w.StatusCurrOp AS NVARCHAR(128)), CAST(w.CurrentOperation AS NVARCHAR(128)), N'NO OPERATIONS - SET TO UNRELEASED') StatusCurrOpMsg
	, ISNULL(W.col_USER_1 + ',  ','') + ISNULL(l.[DESCRIPTION] + CHAR(10) + CHAR(13), '') + ISNULL('PO '+ dslPO.ID + ' - ', '') 
		+ ISNULL(CONVERT(NVARCHAR(12), ISNULL(dslPO.PROMISE_SHIP_DATE,dslPO.DESIRED_RECV_DATE), 110), '') AS tdesc
	, l.[DESCRIPTION] AS LABOR_TICKET_DESC
	, ISNULL(CASE WHEN p.COMMODITY_CODE = 'Details' THEN COALESCE(leg.Salesperson_ID, b.Salesperson_ID, c.SALESREP_ID) + '-D' ELSE COALESCE(leg.Salesperson_ID, b.Salesperson_ID, c.SALESREP_ID) END,  '_blank')  BUYER
	, COALESCE(leg.Salesperson_ID, b.Salesperson_ID, c.SALESREP_ID, '_blank') AS BUYERFILTER
	, COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') AS SALESREP_ID  
	, ISNULL(b.Account_ID,'00') AS Account
	, ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') AS Plant_ID
	, CASE WHEN p.COMMODITY_CODE = 'Tools' THEN 1 ELSE 0 END AS Tooling
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' AND w.STATUS = 'R' THEN 1 ELSE 0 END AS IsAP1
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP2' AND w.STATUS = 'R' THEN 1 ELSE 0 END AS IsAP2
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP3' AND w.STATUS = 'R' THEN 1 ELSE 0 END AS IsAP3
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'BP1' AND w.STATUS = 'R' THEN 1 ELSE 0 END AS IsBP1
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'Undetermined' THEN 1 ELSE 0 END AS IsUndetermined
	, CASE WHEN w.CUSTOMER_ID = 'NORGRU' THEN 1 ELSE 0 END AS IsNORGRU
	, CASE WHEN w.CUSTOMER_ID = 'TWMETA' THEN 1 ELSE 0 END AS IsTWMETA
	, CASE WHEN w.CUSTOMER_ID = 'AMTRIB' THEN 1 ELSE 0 END AS IsAMTRIB
	, CASE WHEN ISNULL(rs.IsAUBMASK, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBMASK
	, CASE WHEN ISNULL(rs.IsAubPrime, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBPrime
	, CASE WHEN ISNULL(rs.IsAUBSand, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBSand
	, CASE WHEN ISNULL(rs.IsAUBsetup, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBsetup
	, CASE WHEN ISNULL(rs.IsAUBTC, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBTC
	, CASE WHEN ISNULL(rs.IsAUBtakedown, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBtakedown
	, CASE WHEN ISNULL(rs.IsAUBPartMark, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBPartMark
	, CASE WHEN ISNULL(rs.IsAUBFinalInspection, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBFinalInspection
	, CASE WHEN ISNULL(rs.IsAUBInspection, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBInspection
	, CASE WHEN ISNULL(rs.IsAUBPenetrant, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBPenetrant
	, CASE WHEN ISNULL(rs.IsAUBChemline, -1) <> -1 THEN 1 ELSE 0 END AS IsAUBChemline
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' AND w.[EXP/FLT] = '1_ETRAC' THEN 1 ELSE 0 END AS AP1_ETRAC
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP2' AND w.[EXP/FLT] = '1_ETRAC' THEN 1 ELSE 0 END AS AP2_ETRAC
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP3' AND w.[EXP/FLT] = '1_ETRAC' THEN 1 ELSE 0 END AS AP3_ETRAC
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'BP1' AND w.[EXP/FLT] = '1_ETRAC' THEN 1 ELSE 0 END AS BP1_ETRAC
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' AND w.[EXP/FLT] IN ('3_PD EXP', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP1_PDEXP
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP2' AND w.[EXP/FLT] IN ('3_PD EXP', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP2_PDEXP
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP3' AND w.[EXP/FLT] IN ('3_PD EXP', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP3_PDEXP
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'BP1' AND w.[EXP/FLT] IN ('3_PD EXP', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS BP1_PDEXP
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' AND w.[EXP/FLT] IN ('5_FLT', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP1_FLT
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP2' AND w.[EXP/FLT] IN ('5_FLT', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP2_FLT
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP3' AND w.[EXP/FLT] IN ('5_FLT', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS AP3_FLT
	, CASE WHEN ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'BP1' AND w.[EXP/FLT] IN ('5_FLT', '4_PD EXP/FLT') THEN 1 ELSE 0 END AS BP1_FLT
--> tt20190816
	--	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Tracy' AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' THEN 1 ELSE 0 END AS AP1_Buyer_Tracy
	--	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Meg' AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' THEN 1 ELSE 0 END AS AP1_Buyer_Meg
	--	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Sharon' AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' THEN 1 ELSE 0 END AS AP1_Buyer_Sharon
 	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Joe' AND ISNULL(CAST(sr.USER_5 AS NVARCHAR(30)), 'Undetermined') = 'AP1' THEN 1 ELSE 0 END AS AP1_Buyer_Joe
--> tt20181113
	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Rena' THEN 1 ELSE 0 END AS AP1_Buyer_Rena
	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Tiffany' THEN 1 ELSE 0 END AS AP1_Buyer_Tiffany
	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Sunni' THEN 1 ELSE 0 END AS AP1_Buyer_Sunni
	, CASE WHEN COALESCE(b.Salesperson_ID, c.SALESREP_ID, '_blank') = 'Danielle' THEN 1 ELSE 0 END AS AP1_Buyer_Danielle
	, CASE WHEN w.STATUS = 'R' AND ISNULL(rs.AP1_Review, -1) <> -1 THEN 1 ELSE 0 END AS AP1_Review
	, CASE WHEN w.STATUS IN ('U','F') AND sr.USER_5 IN ('AP1', 'BP1') THEN 1 ELSE 0 END AS AP1_PlanningQueue
	, CASE WHEN ISNULL(sr.USER_8, '_blank') = 'CARGO' THEN 1 ELSE 0 END AS AP1_SkyFlex
	, dslPO.ID
	, ISNULL(dslPO.PROMISE_SHIP_DATE, dslPO.DESIRED_RECV_DATE) AS DESIRED_RECV_DATE
	, GETDATE() AS SnapshotDate
--> tt20190424 
	, SR.USER_2 AS DEPARTMENT
	, SR.USER_3 AS SUB_DEPARTMENT
--> tt20191120
	, SR.USER_5 AS FACILITY
	, SR.USER_6 AS REPT_DEPT
	, SR.USER_7 AS PROCESS
	, SR.USER_8 AS REPORT_GROUPING
	, CASE
		WHEN LTRIM(RTRIM(sr.USER_4)) = 'GREG HARTMAN' THEN 'GREGH@SKILLSINC.COM'
		ELSE EE.EMAIL_ADDR
	END AS EMAIL_ADDR
	, W.SETUP_INFO
into #temp1
FROM cte_currentoperation w
LEFT JOIN cte_labortickets l
	ON w.BASE_ID = l.WORKORDER_BASE_ID
	AND w.LOT_ID = l.WORKORDER_LOT_ID
	AND w.SPLIT_ID = l.WORKORDER_SPLIT_ID
	AND w.SUB_ID = l.WORKORDER_SUB_ID
	AND w.[TYPE] = l.WORKORDER_TYPE
--> TT20210727: add last closed date
LEFT JOIN CTE_LASTOPCLOSED LO
	ON W.BASE_ID = LO.WORKORDER_BASE_ID
	AND W.LOT_ID = LO.WORKORDER_LOT_ID
	AND W.SPLIT_ID = LO.WORKORDER_SPLIT_ID
	AND W.SUB_ID = LO.WORKORDER_SUB_ID
	AND W.[TYPE] = LO.WORKORDER_TYPE
LEFT JOIN EMPLOYEE e
	ON e.ID = l.EMPLOYEE_ID
LEFT JOIN SHOP_RESOURCE_SITE_VIEW SR
	ON SR.RESOURCE_ID = w.RESOURCE_ID_Raw
--> tt20190424
LEFT OUTER JOIN EMPLOYEE EE
	ON LTRIM(RTRIM(sr.USER_4)) = EE.[FIRST_NAME] + ' ' + EE.[LAST_NAME]
	AND EE.ACTIVE = 'Y'
LEFT JOIN LIVESupplemental.dbo.buyer_assn b
	ON LEFT(w.BUYER_USER_ID,2) = b.Account_ID
LEFT JOIN CUSTOMER c
	ON c.ID = w.CUSTOMER_ID
LEFT JOIN PART_SITE_VIEW P
	ON P.PART_ID = w.PART_ID
	AND P.SITE_ID = 'SK01'
	AND w.SUB_ID <> N'0'
LEFT JOIN LIVESupplemental.dbo.buyer_assn leg
	ON leg.Account_ID = LEFT(P.BUYER_USER_ID, 2)
LEFT JOIN (SELECT PO.ID
		, dslPO.DEMAND_BASE_ID
		, DEMAND_LOT_ID
		, DEMAND_SUB_ID
		, DEMAND_SPLIT_ID
		, dslPO.DEMAND_SEQ_NO
		, PO.DESIRED_RECV_DATE
		, PO.PROMISE_SHIP_DATE 
	FROM PURCHASE_ORDER PO
	JOIN DEMAND_SUPPLY_LINK dslPO
		ON dslPO.SUPPLY_BASE_ID = PO.ID
	GROUP BY PO.ID
		, dslPO.DEMAND_BASE_ID
		, DEMAND_LOT_ID
		, DEMAND_SUB_ID
		, DEMAND_SPLIT_ID
		, dslPO.DEMAND_SEQ_NO
		, PO.DESIRED_RECV_DATE
		, PO.PROMISE_SHIP_DATE
	) dslPO
	ON dslPO.DEMAND_BASE_ID = w.BASE_ID
	AND dslPO.DEMAND_LOT_ID = w.LOT_ID
	AND dslPO.DEMAND_SUB_ID = w.SUB_ID
	AND dslPO.DEMAND_SPLIT_ID = w.SPLIT_ID
	AND dslPO.DEMAND_SEQ_NO = w.CurrentOperation
LEFT JOIN @ReportSettings rs
	ON w.RESOURCE_ID_Raw = rs.Resource

--SELECT * FROM #temp1 where base_id = '1659369'
--SELECT * FROM #temp1 where PART_ID = '415Z4003-5'

--wods_query_ends:

--output_data_in_test:

TRUNCATE TABLE Staging.WODS_Output01
INSERT INTO Staging.WODS_Output01
([BASE_ID]
	, [LOT_ID]
	, [SPLIT_ID]
	, [SUB_ID]
	, [TYPE]
	, [PART_ID]
	, [WONUM]
	, [DESIRED_QTY]
	, [STATUS]
	, [CUSTOMER_ORDER]
	, [LINE_NO]
	, [CUSTOMER_ID]
	, [allocation_type]
	, [CurrentOperation]
	, [StatusCurrOp]
	, [PRINTED_DATE]
	, [DESIRED_RLS_DATE]
	, [CREATE_DATE]
	, [remaining_operations]
	, [QTY_ON_HAND]
	, [QTY_IN_DEMAND]
	, [BUYER_USER_ID]
	, [PLANNER_USER_ID]
	, [COMMODITY_CODE]
	, [DESCRIPTION]
	, [DESIRED_WANT_DATE]
	, [EXP/FLT]
	, [user_10]
	, [col_user_1]
	, [RWPart]
	, [CUSTOMER_PO_REF]
	, [WORK_ORDER_NOTES]
	, [CUST_ORDER_NOTATION]
	, [CUST_ORD_CREATEDATE]
	, [PartMaterialType]
	, [MaterialType]
	, [Alloy]
	, [CO_AMOUNT]
	, [UNIT_PRICE]
	, [TOTAL_AMT_SHIPPED]
	, [COL_AMOUNT]
	, [RESOURCE_ID_Raw]
	, [OPERATION_TYPE]
	, [StatusCurrOpType]
	, [CURROPCHK]
	, [RESOURCE_ID]
	, [AubPriText]
	, [AubTcText]
	, [HasAubPri]
	, [HasAubTc]
	, [TimeLimit]
	, [LAST_CLOCK_OUT]
	, [last_worked_seq]
	, [last_clocked]
	, [LATE]
	, [LATEP2]
	, [LATEP1]
	, [LATEP3]
	, [LATEBP1]
	, [WAIT_DAYS]
	, [EMPLOYEE_ID]
	, [OPERATOR]
	, [USER_1]
	, [LEAD_SUPERVISOR]
	, [SupervisorName]
	, [StatusCurrOpMsg]
	, [tdesc]
	, [LABOR_TICKET_DESC]
	, [BUYER]
	, [BUYERFILTER]
	, [SALESREP_ID]
	, [Account]
	, [Plant_ID]
	, [Tooling]
	, [IsAP1]
	, [IsAP2]
	, [IsAP3]
	, [IsBP1]
	, [IsUndetermined]
	, [IsNORGRU]
	, [IsTWMETA]
	, [IsAMTRIB]
	, [IsAUBMASK]
	, [IsAUBPrime]
	, [IsAUBSand]
	, [IsAUBsetup]
	, [IsAUBTC]
	, [IsAUBtakedown]
	, [IsAUBPartMark]
	, [IsAUBFinalInspection]
	, [IsAUBInspection]
	, [IsAUBPenetrant]
	, [IsAUBChemline]
	, [AP1_ETRAC]
	, [AP2_ETRAC]
	, [AP3_ETRAC]
	, [BP1_ETRAC]
	, [AP1_PDEXP]
	, [AP2_PDEXP]
	, [AP3_PDEXP]
	, [BP1_PDEXP]
	, [AP1_FLT]
	, [AP2_FLT]
	, [AP3_FLT]
	, [BP1_FLT]
	, [AP1_Buyer_Joe]
	, [AP1_Buyer_Rena]
	, [AP1_Buyer_Tiffany]
	, [AP1_Buyer_Sunni]
	, [AP1_Buyer_Danielle]
	, [AP1_Review]
	, [AP1_PlanningQueue]
	, [AP1_SkyFlex]
	, [ID]
	, [DESIRED_RECV_DATE]
	, [SnapshotDate]
	, [DEPARTMENT]
	, [SUB_DEPARTMENT]
	, [FACILITY]
	, [REPT_DEPT]
	, [PROCESS]
	, [REPORT_GROUPING]
	, [EMAIL_ADDR]
	, [SETUP_INFO]
	)
SELECT [BASE_ID]
	, [LOT_ID]
	, [SPLIT_ID]
	, [SUB_ID]
	, [TYPE]
	, [PART_ID]
	, [WONUM]
	, [DESIRED_QTY]
	, [STATUS]
	, [CUSTOMER_ORDER]
	, [LINE_NO]
	, [CUSTOMER_ID]
	, [allocation_type]
	, [CurrentOperation]
	, [StatusCurrOp]
	, [PRINTED_DATE]
	, [DESIRED_RLS_DATE]
	, [CREATE_DATE]
	, [remaining_operations]
	, [QTY_ON_HAND]
	, [QTY_IN_DEMAND]
	, [BUYER_USER_ID]
	, [PLANNER_USER_ID]
	, [COMMODITY_CODE]
	, [DESCRIPTION]
	, [DESIRED_WANT_DATE]
	, [EXP/FLT]
	, [user_10]
	, [col_user_1]
	, [RWPart]
	, [CUSTOMER_PO_REF]
	, [WORK_ORDER_NOTES]
	, [CUST_ORDER_NOTATION]
	, [CUST_ORD_CREATEDATE]
	, [PartMaterialType]
	, [MaterialType]
	, [Alloy]
	, [CO_AMOUNT]
	, [UNIT_PRICE]
	, [TOTAL_AMT_SHIPPED]
	, [COL_AMOUNT]
	, [RESOURCE_ID_Raw]
	, [OPERATION_TYPE]
	, [StatusCurrOpType]
	, [CURROPCHK]
	, [RESOURCE_ID]
	, [AubPriText]
	, [AubTcText]
	, [HasAubPri]
	, [HasAubTc]
	, [TimeLimit]
	, [LAST_CLOCK_OUT]
	, [last_worked_seq]
	, [last_clocked]
	, [LATE]
	, [LATEP2]
	, [LATEP1]
	, [LATEP3]
	, [LATEBP1]
	, [WAIT_DAYS]
	, [EMPLOYEE_ID]
	, [OPERATOR]
	, [USER_1]
	, [LEAD_SUPERVISOR]
	, [SupervisorName]
	, [StatusCurrOpMsg]
	, [tdesc]
	, [LABOR_TICKET_DESC]
	, [BUYER]
	, [BUYERFILTER]
	, [SALESREP_ID]
	, [Account]
	, [Plant_ID]
	, [Tooling]
	, [IsAP1]
	, [IsAP2]
	, [IsAP3]
	, [IsBP1]
	, [IsUndetermined]
	, [IsNORGRU]
	, [IsTWMETA]
	, [IsAMTRIB]
	, [IsAUBMASK]
	, [IsAUBPrime]
	, [IsAUBSand]
	, [IsAUBsetup]
	, [IsAUBTC]
	, [IsAUBtakedown]
	, [IsAUBPartMark]
	, [IsAUBFinalInspection]
	, [IsAUBInspection]
	, [IsAUBPenetrant]
	, [IsAUBChemline]
	, [AP1_ETRAC]
	, [AP2_ETRAC]
	, [AP3_ETRAC]
	, [BP1_ETRAC]
	, [AP1_PDEXP]
	, [AP2_PDEXP]
	, [AP3_PDEXP]
	, [BP1_PDEXP]
	, [AP1_FLT]
	, [AP2_FLT]
	, [AP3_FLT]
	, [BP1_FLT]
	, [AP1_Buyer_Joe]
	, [AP1_Buyer_Rena]
	, [AP1_Buyer_Tiffany]
	, [AP1_Buyer_Sunni]
	, [AP1_Buyer_Danielle]
	, [AP1_Review]
	, [AP1_PlanningQueue]
	, [AP1_SkyFlex]
	, [ID]
	, [DESIRED_RECV_DATE]
	, [SnapshotDate]
	, [DEPARTMENT]
	, [SUB_DEPARTMENT]
	, [FACILITY]
	, [REPT_DEPT]
	, [PROCESS]
	, [REPORT_GROUPING]
	, [EMAIL_ADDR]
	, [SETUP_INFO]
FROM (SELECT [BASE_ID]
	, [LOT_ID]
	, [SPLIT_ID]
	, [SUB_ID]
	, [TYPE]
	, [PART_ID]
	, [WONUM]
	, [DESIRED_QTY]
	, [STATUS]
	, [CUSTOMER_ORDER]
	, [LINE_NO]
	, [CUSTOMER_ID]
	, [allocation_type]
	, [CurrentOperation]
	, [StatusCurrOp]
	, [PRINTED_DATE]
	, [DESIRED_RLS_DATE]
	, [CREATE_DATE]
	, [remaining_operations]
	, [QTY_ON_HAND]
	, [QTY_IN_DEMAND]
	, [BUYER_USER_ID]
	, [PLANNER_USER_ID]
	, [COMMODITY_CODE]
	, [DESCRIPTION]
	, [DESIRED_WANT_DATE]
	, [EXP/FLT]
	, [user_10]
	, [col_user_1]
	, [RWPart]
	, [CUSTOMER_PO_REF]
	, [WORK_ORDER_NOTES]
	, [CUST_ORDER_NOTATION]
	, [CUST_ORD_CREATEDATE]
	, [PartMaterialType]
	, [MaterialType]
	, [Alloy]
	, [CO_AMOUNT]
	, [UNIT_PRICE]
	, [TOTAL_AMT_SHIPPED]
	, [COL_AMOUNT]
	, [RESOURCE_ID_Raw]
	, [OPERATION_TYPE]
	, [StatusCurrOpType]
	, [CURROPCHK]
	, [RESOURCE_ID]
	, [AubPriText]
	, [AubTcText]
	, [HasAubPri]
	, [HasAubTc]
	, [TimeLimit]
	, [LAST_CLOCK_OUT]
	, [last_worked_seq]
	, [last_clocked]
	, [LATE]
	, [LATEP2]
	, [LATEP1]
	, [LATEP3]
	, [LATEBP1]
	, [WAIT_DAYS]
	, [EMPLOYEE_ID]
	, [OPERATOR]
	, [USER_1]
	, [LEAD_SUPERVISOR]
	, [SupervisorName]
	, [StatusCurrOpMsg]
	, [tdesc]
	, [LABOR_TICKET_DESC]
	, [BUYER]
	, [BUYERFILTER]
	, [SALESREP_ID]
	, [Account]
	, [Plant_ID]
	, [Tooling]
	, [IsAP1]
	, [IsAP2]
	, [IsAP3]
	, [IsBP1]
	, [IsUndetermined]
	, [IsNORGRU]
	, [IsTWMETA]
	, [IsAMTRIB]
	, [IsAUBMASK]
	, [IsAUBPrime]
	, [IsAUBSand]
	, [IsAUBsetup]
	, [IsAUBTC]
	, [IsAUBtakedown]
	, [IsAUBPartMark]
	, [IsAUBFinalInspection]
	, [IsAUBInspection]
	, [IsAUBPenetrant]
	, [IsAUBChemline]
	, [AP1_ETRAC]
	, [AP2_ETRAC]
	, [AP3_ETRAC]
	, [BP1_ETRAC]
	, [AP1_PDEXP]
	, [AP2_PDEXP]
	, [AP3_PDEXP]
	, [BP1_PDEXP]
	, [AP1_FLT]
	, [AP2_FLT]
	, [AP3_FLT]
	, [BP1_FLT]
	, [AP1_Buyer_Joe]
	, [AP1_Buyer_Rena]
	, [AP1_Buyer_Tiffany]
	, [AP1_Buyer_Sunni]
	, [AP1_Buyer_Danielle]
	, [AP1_Review]
	, [AP1_PlanningQueue]
	, [AP1_SkyFlex]
	, [ID]
	, [DESIRED_RECV_DATE]
	, [SnapshotDate]
	, [DEPARTMENT]
	, [SUB_DEPARTMENT]
	, [FACILITY]
	, [REPT_DEPT]
	, [PROCESS]
	, [REPORT_GROUPING]
	, [EMAIL_ADDR]
	, [SETUP_INFO]
	, rn = ROW_NUMBER() OVER (PARTITION BY wonum ORDER BY t.[LINE_NO], part_id)
FROM #temp1 t (NOLOCK)
) X
WHERE X.rn = 1

merge_data:

SET NOCOUNT OFF
DECLARE @TransactionStartDate DATETIME2(7) = SYSDATETIME()
	, @TransactionEndDate DATETIME2(7)
	, @StoredProcedureStartDate DATETIME2(7) = SYSDATETIME()
	, @DurationSeconds INT
	, @Rows INT = 0
	, @RowsPerSecond INT
	, @Error INT
	, @InsertedRows INT = 0
	, @UpdatedRows INT = 0
	, @DeletedRows INT = 0
	, @StoredProcedureName SYSNAME = 
		(SELECT @@SERVERNAME + '.' + DB_NAME() + '.' + s.name + '.' + o.name 
		FROM sys.objects o (NOLOCK) 
		JOIN sys.schemas s (NOLOCK) 
			ON o.schema_id = s.schema_id 
		WHERE o.object_id = @@PROCID)
	, @TargetServer SYSNAME = @@SERVERNAME
	, @TargetDatabase SYSNAME = 'DataWarehouse'
	, @TargetSchema SYSNAME = 'dbo'
	, @TargetTable SYSNAME = 'Wods_Output'
	, @StepId INT = 1
	, @Step VARCHAR(4000)

DECLARE @MergeResult TABLE (ActionTaken VARCHAR(20) NOT NULL);

MERGE LiveSupplemental.dbo.WODS_Output Trgt
USING Staging.WODS_Output01 SRC (NOLOCK)
ON Trgt.WONUM = SRC.WONUM

WHEN MATCHED AND

    trgt.BASE_ID <> src.BASE_ID
 or trgt.LOT_ID <> src.LOT_ID
 OR trgt.SPLIT_ID <> src.SPLIT_ID
 OR trgt.SUB_ID <> src.SUB_ID
 OR trgt.TYPE <> src.TYPE
 OR ISNULL(trgt.PART_ID, '') <> ISNULL(src.PART_ID, '')

 OR ISNULL(trgt.DESIRED_QTY, -30000) <> ISNULL(src.DESIRED_QTY, -30000)
 OR trgt.STATUS <> src.STATUS
 OR ISNULL(trgt.CUSTOMER_ORDER, '') <> ISNULL(src.CUSTOMER_ORDER, '')
 OR ISNULL(trgt.LINE_NO, -30000) <> ISNULL(src.LINE_NO, -30000)
 OR ISNULL(trgt.CUSTOMER_ID, '') <> ISNULL(src.CUSTOMER_ID, '')
 OR ISNULL(trgt.allocation_type, '') <> ISNULL(src.allocation_type, '')
 OR ISNULL(trgt.CurrentOperation, -30000) <> ISNULL(src.CurrentOperation, -30000)
 OR ISNULL(trgt.StatusCurrOp, -30000) <> ISNULL(src.StatusCurrOp, -30000)
 OR ISNULL(trgt.PRINTED_DATE, '1/1/1990') <> ISNULL(src.PRINTED_DATE, '1/1/1990')
 OR ISNULL(trgt.DESIRED_RLS_DATE, '1/1/1990') <> ISNULL(src.DESIRED_RLS_DATE, '1/1/1990')
 OR trgt.CREATE_DATE <> src.CREATE_DATE
 OR trgt.remaining_operations <> src.remaining_operations
 OR trgt.QTY_ON_HAND <> src.QTY_ON_HAND
 OR trgt.QTY_IN_DEMAND <> src.QTY_IN_DEMAND
 OR ISNULL(trgt.BUYER_USER_ID, '') <> ISNULL(src.BUYER_USER_ID, '')
 OR ISNULL(trgt.PLANNER_USER_ID, '') <> ISNULL(src.PLANNER_USER_ID, '')
 OR ISNULL(trgt.COMMODITY_CODE, '') <> ISNULL(src.COMMODITY_CODE, '')
 OR ISNULL(trgt.DESCRIPTION, '') <> ISNULL(src.DESCRIPTION, '')
 OR ISNULL(trgt.DESIRED_WANT_DATE, '1/1/1990') <> ISNULL(src.DESIRED_WANT_DATE, '1/1/1990')
 OR ISNULL(trgt.[EXP/FLT], '') <> ISNULL(src.[EXP/FLT], '')
 OR ISNULL(trgt.user_10, '') <> ISNULL(src.user_10, '')
 OR ISNULL(trgt.col_user_1, '') <> ISNULL(src.col_user_1, '')
 OR ISNULL(trgt.RWPart, '') <> ISNULL(src.RWPart, '')
 OR ISNULL(trgt.CUSTOMER_PO_REF, '') <> ISNULL(src.CUSTOMER_PO_REF, '')
 OR ISNULL(trgt.WORK_ORDER_NOTES, '') <> ISNULL(src.WORK_ORDER_NOTES, '')
 OR ISNULL(trgt.CUST_ORDER_NOTATION, '') <> ISNULL(src.CUST_ORDER_NOTATION, '')
 OR ISNULL(trgt.CUST_ORD_CREATEDATE, '1/1/1990') <> ISNULL(src.CUST_ORD_CREATEDATE, '1/1/1990')
 OR trgt.PartMaterialType <> src.PartMaterialType
 OR trgt.MaterialType <> src.MaterialType
 OR trgt.Alloy <> src.Alloy
 OR ISNULL(trgt.CO_AMOUNT, -30000) <> ISNULL(src.CO_AMOUNT, -30000)
 OR ISNULL(trgt.UNIT_PRICE, -30000) <> ISNULL(src.UNIT_PRICE, -30000)
 OR ISNULL(trgt.TOTAL_AMT_SHIPPED, -30000) <> ISNULL(src.TOTAL_AMT_SHIPPED, -30000)
 OR ISNULL(trgt.COL_AMOUNT, -30000) <> ISNULL(src.COL_AMOUNT, -30000)
 OR ISNULL(trgt.RESOURCE_ID_Raw, '') <> ISNULL(src.RESOURCE_ID_Raw, '')
 OR ISNULL(trgt.OPERATION_TYPE, '') <> ISNULL(src.OPERATION_TYPE, '')
 OR ISNULL(trgt.StatusCurrOpType, '') <> ISNULL(src.StatusCurrOpType, '')
 OR ISNULL(trgt.CURROPCHK, -30000) <> ISNULL(src.CURROPCHK, -30000)
 OR ISNULL(trgt.RESOURCE_ID, '') <> ISNULL(src.RESOURCE_ID, '')
 OR ISNULL(trgt.AubPriText, '') <> ISNULL(src.AubPriText, '')
 OR ISNULL(trgt.AubTcText, '') <> ISNULL(src.AubTcText, '')
 OR trgt.HasAubPri <> src.HasAubPri
 OR trgt.HasAubTc <> src.HasAubTc
 OR ISNULL(trgt.TimeLimit, -30000) <> ISNULL(src.TimeLimit, -30000)
 OR ISNULL(trgt.LAST_CLOCK_OUT, '1/1/1990') <> ISNULL(src.LAST_CLOCK_OUT, '1/1/1990')
 OR ISNULL(trgt.last_worked_seq, -30000) <> ISNULL(src.last_worked_seq, -30000)
 OR ISNULL(trgt.last_clocked, '') <> ISNULL(src.last_clocked, '')
 OR trgt.LATE <> src.LATE
 OR trgt.LATEP2 <> src.LATEP2
 OR trgt.LATEP1 <> src.LATEP1
 OR trgt.LATEP3 <> src.LATEP3
 OR trgt.LATEBP1 <> src.LATEBP1
 OR trgt.WAIT_DAYS <> src.WAIT_DAYS
 OR ISNULL(trgt.EMPLOYEE_ID, '') <> ISNULL(src.EMPLOYEE_ID, '')
 OR trgt.OPERATOR <> src.OPERATOR
 OR ISNULL(trgt.USER_1, '') <> ISNULL(src.USER_1, '')
 OR ISNULL(trgt.LEAD_SUPERVISOR, '') <> ISNULL(src.LEAD_SUPERVISOR, '')
 OR ISNULL(trgt.SupervisorName, '') <> ISNULL(src.SupervisorName, '')
 OR ISNULL(trgt.StatusCurrOpMsg, '') <> ISNULL(src.StatusCurrOpMsg, '')
 OR trgt.tdesc <> src.tdesc
 OR ISNULL(trgt.LABOR_TICKET_DESC, '') <> ISNULL(src.LABOR_TICKET_DESC, '')
 OR trgt.BUYER <> src.BUYER
 OR ISNULL(trgt.BUYERFILTER, '') <> ISNULL(src.BUYERFILTER, '')
 OR ISNULL(trgt.SALESREP_ID, '') <> ISNULL(src.SALESREP_ID, '')
 OR trgt.Account <> src.Account
 OR trgt.Plant_ID <> src.Plant_ID
 OR trgt.Tooling <> src.Tooling
 OR trgt.IsAP1 <> src.IsAP1
 OR trgt.IsAP2 <> src.IsAP2
 OR trgt.IsAP3 <> src.IsAP3
 OR trgt.IsBP1 <> src.IsBP1
 OR trgt.IsUndetermined <> src.IsUndetermined
 OR trgt.IsNORGRU <> src.IsNORGRU
 OR trgt.IsTWMETA <> src.IsTWMETA
 OR trgt.IsAMTRIB <> src.IsAMTRIB
 OR trgt.IsAUBMASK <> src.IsAUBMASK
 OR trgt.IsAUBPrime <> src.IsAUBPrime
 OR trgt.IsAUBSand <> src.IsAUBSand
 OR trgt.IsAUBsetup <> src.IsAUBsetup
 OR trgt.IsAUBTC <> src.IsAUBTC
 OR trgt.IsAUBtakedown <> src.IsAUBtakedown
 OR trgt.IsAUBPartMark <> src.IsAUBPartMark
 OR trgt.IsAUBFinalInspection <> src.IsAUBFinalInspection
 OR trgt.IsAUBInspection <> src.IsAUBInspection
 OR trgt.IsAUBPenetrant <> src.IsAUBPenetrant
 OR trgt.IsAUBChemline <> src.IsAUBChemline
 OR trgt.AP1_ETRAC <> src.AP1_ETRAC
 OR trgt.AP2_ETRAC <> src.AP2_ETRAC
 OR trgt.AP3_ETRAC <> src.AP3_ETRAC
 OR trgt.BP1_ETRAC <> src.BP1_ETRAC
 OR trgt.AP1_PDEXP <> src.AP1_PDEXP
 OR trgt.AP2_PDEXP <> src.AP2_PDEXP
 OR trgt.AP3_PDEXP <> src.AP3_PDEXP
 OR trgt.BP1_PDEXP <> src.BP1_PDEXP
 OR trgt.AP1_FLT <> src.AP1_FLT
 OR trgt.AP2_FLT <> src.AP2_FLT
 OR trgt.AP3_FLT <> src.AP3_FLT
 OR trgt.BP1_FLT <> src.BP1_FLT
 OR trgt.AP1_Buyer_Joe <> src.AP1_Buyer_Joe
 OR trgt.AP1_Buyer_Rena <> src.AP1_Buyer_Rena
 OR trgt.AP1_Buyer_Tiffany <> src.AP1_Buyer_Tiffany
 OR trgt.AP1_Buyer_Sunni <> src.AP1_Buyer_Sunni
 OR trgt.AP1_Buyer_Danielle <> src.AP1_Buyer_Danielle
 OR trgt.AP1_Review <> src.AP1_Review
 OR trgt.AP1_PlanningQueue <> src.AP1_PlanningQueue
 OR trgt.AP1_SkyFlex <> src.AP1_SkyFlex
 OR ISNULL(trgt.ID, '') <> ISNULL(src.ID, '')
 OR ISNULL(trgt.DESIRED_RECV_DATE, '1/1/1990') <> ISNULL(src.DESIRED_RECV_DATE, '1/1/1990')
 OR trgt.SnapshotDate <> src.SnapshotDate
 OR ISNULL(trgt.DEPARTMENT, '') <> ISNULL(src.DEPARTMENT, '')
 OR ISNULL(trgt.SUB_DEPARTMENT, '') <> ISNULL(src.SUB_DEPARTMENT, '')
 OR ISNULL(trgt.FACILITY, '') <> ISNULL(src.FACILITY, '')
 OR ISNULL(trgt.REPT_DEPT, '') <> ISNULL(src.REPT_DEPT, '')
 OR ISNULL(trgt.PROCESS, '') <> ISNULL(src.PROCESS, '')
 OR ISNULL(trgt.REPORT_GROUPING, '') <> ISNULL(src.REPORT_GROUPING, '')
 OR ISNULL(trgt.EMAIL_ADDR, '') <> ISNULL(src.EMAIL_ADDR, '')
 OR ISNULL(trgt.[SETUP_INFO], '') <> ISNULL(src.[SETUP_INFO], '')

THEN UPDATE SET

   LOT_ID = src.LOT_ID
 , SPLIT_ID = src.SPLIT_ID
 , SUB_ID = src.SUB_ID
 , TYPE = src.TYPE
 , PART_ID = src.PART_ID
 , WONUM = src.WONUM
 , DESIRED_QTY = src.DESIRED_QTY
 , STATUS = src.STATUS
 , CUSTOMER_ORDER = src.CUSTOMER_ORDER
 , LINE_NO = src.LINE_NO
 , CUSTOMER_ID = src.CUSTOMER_ID
 , allocation_type = src.allocation_type
 , CurrentOperation = src.CurrentOperation
 , StatusCurrOp = src.StatusCurrOp
 , PRINTED_DATE = src.PRINTED_DATE
 , DESIRED_RLS_DATE = src.DESIRED_RLS_DATE
 , CREATE_DATE = src.CREATE_DATE
 , remaining_operations = src.remaining_operations
 , QTY_ON_HAND = src.QTY_ON_HAND
 , QTY_IN_DEMAND = src.QTY_IN_DEMAND
 , BUYER_USER_ID = src.BUYER_USER_ID
 , PLANNER_USER_ID = src.PLANNER_USER_ID
 , COMMODITY_CODE = src.COMMODITY_CODE
 , DESCRIPTION = src.DESCRIPTION
 , DESIRED_WANT_DATE = src.DESIRED_WANT_DATE
 , [EXP/FLT] = src.[EXP/FLT]
 , user_10 = src.user_10
 , col_user_1 = src.col_user_1
 , RWPart = src.RWPart
 , CUSTOMER_PO_REF = src.CUSTOMER_PO_REF
 , WORK_ORDER_NOTES = src.WORK_ORDER_NOTES
 , CUST_ORDER_NOTATION = src.CUST_ORDER_NOTATION
 , CUST_ORD_CREATEDATE = src.CUST_ORD_CREATEDATE
 , PartMaterialType = src.PartMaterialType
 , MaterialType = src.MaterialType
 , Alloy = src.Alloy
 , CO_AMOUNT = src.CO_AMOUNT
 , UNIT_PRICE = src.UNIT_PRICE
 , TOTAL_AMT_SHIPPED = src.TOTAL_AMT_SHIPPED
 , COL_AMOUNT = src.COL_AMOUNT
 , RESOURCE_ID_Raw = src.RESOURCE_ID_Raw
 , OPERATION_TYPE = src.OPERATION_TYPE
 , StatusCurrOpType = src.StatusCurrOpType
 , CURROPCHK = src.CURROPCHK
 , RESOURCE_ID = src.RESOURCE_ID
 , AubPriText = src.AubPriText
 , AubTcText = src.AubTcText
 , HasAubPri = src.HasAubPri
 , HasAubTc = src.HasAubTc
 , TimeLimit = src.TimeLimit
 , LAST_CLOCK_OUT = src.LAST_CLOCK_OUT
 , last_worked_seq = src.last_worked_seq
 , last_clocked = src.last_clocked
 , LATE = src.LATE
 , LATEP2 = src.LATEP2
 , LATEP1 = src.LATEP1
 , LATEP3 = src.LATEP3
 , LATEBP1 = src.LATEBP1
 , WAIT_DAYS = src.WAIT_DAYS
 , EMPLOYEE_ID = src.EMPLOYEE_ID
 , OPERATOR = src.OPERATOR
 , USER_1 = src.USER_1
 , LEAD_SUPERVISOR = src.LEAD_SUPERVISOR
 , SupervisorName = src.SupervisorName
 , StatusCurrOpMsg = src.StatusCurrOpMsg
 , tdesc = src.tdesc
 , LABOR_TICKET_DESC = src.LABOR_TICKET_DESC
 , BUYER = src.BUYER
 , BUYERFILTER = src.BUYERFILTER
 , SALESREP_ID = src.SALESREP_ID
 , Account = src.Account
 , Plant_ID = src.Plant_ID
 , Tooling = src.Tooling
 , IsAP1 = src.IsAP1
 , IsAP2 = src.IsAP2
 , IsAP3 = src.IsAP3
 , IsBP1 = src.IsBP1
 , IsUndetermined = src.IsUndetermined
 , IsNORGRU = src.IsNORGRU
 , IsTWMETA = src.IsTWMETA
 , IsAMTRIB = src.IsAMTRIB
 , IsAUBMASK = src.IsAUBMASK
 , IsAUBPrime = src.IsAUBPrime
 , IsAUBSand = src.IsAUBSand
 , IsAUBsetup = src.IsAUBsetup
 , IsAUBTC = src.IsAUBTC
 , IsAUBtakedown = src.IsAUBtakedown
 , IsAUBPartMark = src.IsAUBPartMark
 , IsAUBFinalInspection = src.IsAUBFinalInspection
 , IsAUBInspection = src.IsAUBInspection
 , IsAUBPenetrant = src.IsAUBPenetrant
 , IsAUBChemline = src.IsAUBChemline
 , AP1_ETRAC = src.AP1_ETRAC
 , AP2_ETRAC = src.AP2_ETRAC
 , AP3_ETRAC = src.AP3_ETRAC
 , BP1_ETRAC = src.BP1_ETRAC
 , AP1_PDEXP = src.AP1_PDEXP
 , AP2_PDEXP = src.AP2_PDEXP
 , AP3_PDEXP = src.AP3_PDEXP
 , BP1_PDEXP = src.BP1_PDEXP
 , AP1_FLT = src.AP1_FLT
 , AP2_FLT = src.AP2_FLT
 , AP3_FLT = src.AP3_FLT
 , BP1_FLT = src.BP1_FLT
 , AP1_Buyer_Joe = src.AP1_Buyer_Joe
 , AP1_Buyer_Rena = src.AP1_Buyer_Rena
 , AP1_Buyer_Tiffany = src.AP1_Buyer_Tiffany
 , AP1_Buyer_Sunni = src.AP1_Buyer_Sunni
 , AP1_Buyer_Danielle = src.AP1_Buyer_Danielle
 , AP1_Review = src.AP1_Review
 , AP1_PlanningQueue = src.AP1_PlanningQueue
 , AP1_SkyFlex = src.AP1_SkyFlex
 , ID = src.ID
 , DESIRED_RECV_DATE = src.DESIRED_RECV_DATE
 , SnapshotDate = src.SnapshotDate
 , DEPARTMENT = src.DEPARTMENT
 , SUB_DEPARTMENT = src.SUB_DEPARTMENT
 , FACILITY = src.FACILITY
 , REPT_DEPT = src.REPT_DEPT
 , PROCESS = src.PROCESS
 , REPORT_GROUPING = src.REPORT_GROUPING
 , EMAIL_ADDR = src.EMAIL_ADDR
 , [SETUP_INFO] = src.SETUP_INFO
WHEN NOT MATCHED BY TARGET
	THEN INSERT 
	 ( BASE_ID
	, LOT_ID
	, SPLIT_ID
	, SUB_ID
	, TYPE
	, PART_ID
	, WONUM
	, DESIRED_QTY
	, STATUS
	, CUSTOMER_ORDER
	, LINE_NO
	, CUSTOMER_ID
	, allocation_type
	, CurrentOperation
	, StatusCurrOp
	, PRINTED_DATE
	, DESIRED_RLS_DATE
	, CREATE_DATE
	, remaining_operations
	, QTY_ON_HAND
	, QTY_IN_DEMAND
	, BUYER_USER_ID
	, PLANNER_USER_ID
	, COMMODITY_CODE
	, DESCRIPTION
	, DESIRED_WANT_DATE
	, [EXP/FLT]
	, user_10
	, col_user_1
	, RWPart
	, CUSTOMER_PO_REF
	, WORK_ORDER_NOTES
	, CUST_ORDER_NOTATION
	, CUST_ORD_CREATEDATE
	, PartMaterialType
	, MaterialType
	, Alloy
	, CO_AMOUNT
	, UNIT_PRICE
 	, TOTAL_AMT_SHIPPED
	, COL_AMOUNT
	, RESOURCE_ID_Raw
	, OPERATION_TYPE
	, StatusCurrOpType
	, CURROPCHK
	, RESOURCE_ID
	, AubPriText
	, AubTcText
	, HasAubPri
	, HasAubTc
	, TimeLimit
	, LAST_CLOCK_OUT
	, last_worked_seq
	, last_clocked
	, LATE
	, LATEP2
	, LATEP1
	, LATEP3
	, LATEBP1
	, WAIT_DAYS
	, EMPLOYEE_ID
	, OPERATOR
	, USER_1
	, LEAD_SUPERVISOR
	, SupervisorName
	, StatusCurrOpMsg
	, tdesc
	, LABOR_TICKET_DESC
	, BUYER
	, BUYERFILTER
	, SALESREP_ID
	, Account
	, Plant_ID
	, Tooling
	, IsAP1
	, IsAP2
	, IsAP3
	, IsBP1
	, IsUndetermined
	, IsNORGRU
	, IsTWMETA
	, IsAMTRIB
	, IsAUBMASK
	, IsAUBPrime
	, IsAUBSand
	, IsAUBsetup
	, IsAUBTC
	, IsAUBtakedown
	, IsAUBPartMark
	, IsAUBFinalInspection
	, IsAUBInspection
	, IsAUBPenetrant
	, IsAUBChemline
	, AP1_ETRAC
	, AP2_ETRAC
	, AP3_ETRAC
	, BP1_ETRAC
	, AP1_PDEXP
	, AP2_PDEXP
	, AP3_PDEXP
	, BP1_PDEXP
	, AP1_FLT
	, AP2_FLT
	, AP3_FLT
	, BP1_FLT
	, AP1_Buyer_Joe
	, AP1_Buyer_Rena
	, AP1_Buyer_Tiffany
	, AP1_Buyer_Sunni
	, AP1_Buyer_Danielle
	, AP1_Review
	, AP1_PlanningQueue
	, AP1_SkyFlex
	, ID
	, DESIRED_RECV_DATE
	, SnapshotDate
	, DEPARTMENT
	, SUB_DEPARTMENT
	, FACILITY
	, REPT_DEPT
	, PROCESS
	, REPORT_GROUPING
	, EMAIL_ADDR 
	, [SETUP_INFO]
	)

	VALUES (BASE_ID
	, LOT_ID
	, SPLIT_ID
	, SUB_ID
	, TYPE
	, PART_ID
	, WONUM
	, DESIRED_QTY
	, STATUS
	, CUSTOMER_ORDER
	, LINE_NO
	, CUSTOMER_ID
	, allocation_type
	, CurrentOperation
	, StatusCurrOp
	, PRINTED_DATE
	, DESIRED_RLS_DATE
	, CREATE_DATE
	, remaining_operations
	, QTY_ON_HAND
	, QTY_IN_DEMAND
	, BUYER_USER_ID
	, PLANNER_USER_ID
	, COMMODITY_CODE
	, DESCRIPTION
	, DESIRED_WANT_DATE
	, [EXP/FLT]
	, user_10
	, col_user_1
	, RWPart
	, CUSTOMER_PO_REF
	, WORK_ORDER_NOTES
	, CUST_ORDER_NOTATION
	, CUST_ORD_CREATEDATE
	, PartMaterialType
	, MaterialType
	, Alloy
	, CO_AMOUNT
	, UNIT_PRICE
	, TOTAL_AMT_SHIPPED
	, COL_AMOUNT
	, RESOURCE_ID_Raw
	, OPERATION_TYPE
	, StatusCurrOpType
	, CURROPCHK
	, RESOURCE_ID
	, AubPriText
	, AubTcText
	, HasAubPri
	, HasAubTc
	, TimeLimit
	, LAST_CLOCK_OUT
	, last_worked_seq
	, last_clocked
	, LATE
	, LATEP2
	, LATEP1
	, LATEP3
	, LATEBP1
	, WAIT_DAYS
	, EMPLOYEE_ID
	, OPERATOR
	, USER_1
	, LEAD_SUPERVISOR
	, SupervisorName
	, StatusCurrOpMsg
	, tdesc
	, LABOR_TICKET_DESC
	, BUYER
	, BUYERFILTER
	, SALESREP_ID
	, Account
	, Plant_ID
	, Tooling
	, IsAP1
	, IsAP2
	, IsAP3
	, IsBP1
	, IsUndetermined
	, IsNORGRU
	, IsTWMETA
	, IsAMTRIB
	, IsAUBMASK
	, IsAUBPrime
	, IsAUBSand
	, IsAUBsetup
	, IsAUBTC
	, IsAUBtakedown
	, IsAUBPartMark
	, IsAUBFinalInspection
	, IsAUBInspection
	, IsAUBPenetrant
	, IsAUBChemline
	, AP1_ETRAC
	, AP2_ETRAC
	, AP3_ETRAC
	, BP1_ETRAC
	, AP1_PDEXP
	, AP2_PDEXP
	, AP3_PDEXP
	, BP1_PDEXP
	, AP1_FLT
	, AP2_FLT
	, AP3_FLT
	, BP1_FLT
	, AP1_Buyer_Joe
	, AP1_Buyer_Rena
	, AP1_Buyer_Tiffany
	, AP1_Buyer_Sunni
	, AP1_Buyer_Danielle
	, AP1_Review
	, AP1_PlanningQueue
	, AP1_SkyFlex
	, ID
	, DESIRED_RECV_DATE
	, SnapshotDate
	, DEPARTMENT
	, SUB_DEPARTMENT
	, FACILITY
	, REPT_DEPT
	, PROCESS
	, REPORT_GROUPING
	, EMAIL_ADDR  
	, [SETUP_INFO]
		)
WHEN NOT MATCHED BY SOURCE 
    THEN DELETE
	OUTPUT $Action INTO @MergeResult;

GO


