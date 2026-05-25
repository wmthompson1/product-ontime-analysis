USE [LIVE]
GO

/****** Object:  StoredProcedure [dbo].[SP_SK_ETL02_WS]    Script Date: 12/15/2025 9:00:06 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

/**********************************************************************************************
Description:
Sample:
Date      Modified By      Change Description
---------- ------------------ ------------------------------------------------------------

Database name 'tempdb' ignored, referencing object in tempdb.
Msg 208, Level 16, State 0, Line 264
Invalid object name '#WODS_Output_Complement'.
**********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results


DECLARE @Tester int
   ,@Part_ID nvarchar(30) = '71507E-1100153';

declare @wo nvarchar(50) = NULL; -- --  '1801171';
--CREATE PROCEDURE [dbo].SP_SK_ETL02_WS AS
	IF OBJECT_ID('tempdb..#RAW_MATERIAL_WODs') IS NOT NULL DROP TABLE #RAW_MATERIAL_WODs
	IF OBJECT_ID('tempdb..#Prev_Op_WODs') IS NOT NULL DROP TABLE #Prev_Op_WODs
	-- WODS_Output_Complement test.1
	IF OBJECT_ID('tempdb..#WODS_Output_Complement') IS NOT NULL DROP TABLE #WODS_Output_Complement

		/*Delete temporal table to release temporal memory */
	--IF OBJECT_ID('tempdb..#RAW_MATERIAL_WODs') IS NOT NULL DROP TABLE #RAW_MATERIAL_WODs
	--IF OBJECT_ID('tempdb..#Prev_Op_WODs') IS NOT NULL DROP TABLE #Prev_Op_WODs

IF OBJECT_ID('tempdb..#WODS_Output_Complement') IS NOT NULL DROP TABLE #WODS_Output_Complement

-- select * from #WODS_Output_Complement

CREATE TABLE #WODS_Output_Complement (
	[BASE_ID] [nvarchar](30) NOT NULL,
	[LOT_ID] [nvarchar](3) NOT NULL,
	[SPLIT_ID] [nvarchar](3) NOT NULL,
	[SUB_ID] [nvarchar](3) NOT NULL,

	[TYPE] [nchar](1) NOT NULL,
	[PART_ID] [nvarchar](30) NULL,
	[WONUM] [nvarchar](42) NULL,
	[DESIRED_QTY] [decimal](14, 4) NULL,
	[STATUS] [nchar](1) NOT NULL,
	[CUSTOMER_ORDER] [nvarchar](15) NULL,
	[LINE_NO] [smallint] NULL,
	[CUSTOMER_ID] [nvarchar](15) NULL,
	[allocation_type] [varchar](8) NULL,
	[CurrentOperation] [int] NULL,
	[StatusCurrOp] [smallint] NULL,
	[PRINTED_DATE] [datetime] NULL,
	[DESIRED_RLS_DATE] [datetime] NULL,
	[CREATE_DATE] [datetime] NOT NULL,
	[remaining_operations] [nvarchar](max) NOT NULL,
	[QTY_ON_HAND] [decimal](14, 4) NOT NULL,
	[QTY_IN_DEMAND] [decimal](14, 4) NOT NULL,
	[BUYER_USER_ID] [nvarchar](20) NULL,
	[PLANNER_USER_ID] [nvarchar](20) NULL,
	[COMMODITY_CODE] [nvarchar](15) NULL,
	[DESCRIPTION] [nvarchar](120) NULL,
	[DESIRED_WANT_DATE] [datetime] NULL,
	[EXP/FLT] [nvarchar](254) NULL,
	[user_10] [nvarchar](80) NULL,
	[col_user_1] [nvarchar](80) NULL,
	[RWPart] [nvarchar](30) NULL,
	[CUSTOMER_PO_REF] [nvarchar](40) NULL,
	[WORK_ORDER_NOTES] [nvarchar](max) NULL,
	[CUST_ORDER_NOTATION] [nvarchar](max) NULL,
	[CUST_ORD_CREATEDATE] [datetime] NULL,
	[PartMaterialType] [nvarchar](254) NOT NULL,
	[MaterialType] [nvarchar](509) NOT NULL,
	[Alloy] [nvarchar](254) NOT NULL,
	[CO_AMOUNT] [decimal](15, 2) NULL,
	[UNIT_PRICE] [decimal](15, 6) NULL,
	[TOTAL_AMT_SHIPPED] [decimal](15, 2) NULL,
	[COL_AMOUNT] [decimal](15, 2) NULL,
	[RESOURCE_ID_Raw] [nvarchar](15) NULL,
	[OPERATION_TYPE] [nvarchar](15) NULL,
	[StatusCurrOpType] [nvarchar](15) NULL,
	[CURROPCHK] [int] NULL,
	[RESOURCE_ID] [nvarchar](15) NULL,
	[AubPriText] [nvarchar](max) NULL,
	[AubTcText] [nvarchar](max) NULL,
	[HasAubPri] [int] NOT NULL,
	[HasAubTc] [int] NOT NULL,
	[TimeLimit] [int] NULL,
	[LAST_CLOCK_OUT] [datetime] NULL,
	[last_worked_seq] [smallint] NULL,
	[last_clocked] [nvarchar](81) NULL,
	[LATE] [int] NOT NULL,
	[LATEP2] [int] NOT NULL,
	[LATEP1] [int] NOT NULL,
	[LATEP3] [int] NOT NULL,
	[LATEBP1] [int] NOT NULL,
	[WAIT_DAYS] [int] NOT NULL,
	[EMPLOYEE_ID] [nvarchar](15) NULL,
	[OPERATOR] [nvarchar](61) NOT NULL,
	[USER_1] [nvarchar](80) NULL,
	[LEAD_SUPERVISOR] [nvarchar](111) NULL,
	[SupervisorName] [nvarchar](80) NULL,
	[StatusCurrOpMsg] [nvarchar](128) NULL,
	[tdesc] [nvarchar](198) NOT NULL,
	[LABOR_TICKET_DESC] [nvarchar](80) NULL,
	[BUYER] [nvarchar](257) NOT NULL,
	[BUYERFILTER] [nvarchar](255) NULL,
	[SALESREP_ID] [nvarchar](255) NULL,
	[Account] [nvarchar](5) NOT NULL,
	[Plant_ID] [nvarchar](30) NOT NULL,
	[Tooling] [int] NOT NULL,
	[IsAP1] [int] NOT NULL,
	[IsAP1a] [int] NOT NULL,
	[IsAP2] [int] NOT NULL,
	[IsAP2a] [int] NOT NULL,
	[IsAP3] [int] NOT NULL,
	[IsAP3a] [int] NOT NULL,
	[IsBP1] [int] NOT NULL,
	[IsUndetermined] [int] NOT NULL,
	[IsNORGRU] [int] NOT NULL,
	[IsTWMETA] [int] NOT NULL,
	[IsAMTRIB] [int] NOT NULL,
	[IsAUBMASK] [int] NOT NULL,
	[IsAUBPrime] [int] NOT NULL,
	[IsAUBSand] [int] NOT NULL,
	[IsAUBsetup] [int] NOT NULL,
	[IsAUBTC] [int] NOT NULL,
	[IsAUBtakedown] [int] NOT NULL,
	[IsAUBPartMark] [int] NOT NULL,
	[IsAUBFinalInspection] [int] NOT NULL,
	[IsAUBInspection] [int] NOT NULL,
	[IsAUBPenetrant] [int] NOT NULL,
	[IsAUBChemline] [int] NOT NULL,
	[AP1_ETRAC] [int] NOT NULL,
	[AP2_ETRAC] [int] NOT NULL,
	[AP3_ETRAC] [int] NOT NULL,
	[BP1_ETRAC] [int] NOT NULL,
	[AP1_PDEXP] [int] NOT NULL,
	[AP2_PDEXP] [int] NOT NULL,
	[AP3_PDEXP] [int] NOT NULL,
	[BP1_PDEXP] [int] NOT NULL,
	[AP1_FLT] [int] NOT NULL,
	[AP2_FLT] [int] NOT NULL,
	[AP3_FLT] [int] NOT NULL,
	[BP1_FLT] [int] NOT NULL,
	[AP1_Buyer_Joe] [int] NOT NULL,
	[AP1_Buyer_Rena] [int] NOT NULL,
	[AP1_Buyer_Tiffany] [int] NOT NULL,
	[AP1_Buyer_Sunni] [int] NOT NULL,
	[AP1_Buyer_Danielle] [int] NOT NULL,
	[AP1_Review] [int] NOT NULL,
	[AP1_PlanningQueue] [int] NOT NULL,
	[AP1_SkyFlex] [int] NOT NULL,
	[ID] [nvarchar](15) NULL,
	[DESIRED_RECV_DATE] [datetime] NULL,
	[SnapshotDate] [datetime] NOT NULL,
	[DEPARTMENT] [nvarchar](80) NULL,
	[SUB_DEPARTMENT] [nvarchar](80) NULL,
	[FACILITY] [nvarchar](80) NULL,
	[REPT_DEPT] [nvarchar](80) NULL,
	[PROCESS] [nvarchar](80) NULL,
	[REPORT_GROUPING] [nvarchar](80) NULL,
	[EMAIL_ADDR] [nvarchar](80) NULL,
	[SETUP_INFO] [nvarchar](80) NULL,
	[RLS_MT] [nvarchar](800) NULL,
	[RM_READY] [nvarchar](800) NULL,
	[remaining_operations_2] [nvarchar](max) NULL,
	[P1F1_RecibedWO_Date] [nvarchar](800) NULL
) 




SET NOCOUNT ON; 



	/* create new temporal table */
	CREATE TABLE #RAW_MATERIAL_WODs (WO nvarchar(60), LOT nvarchar(6), SPLIT nvarchar(6), SUB nvarchar(6), PART_ID varchar(48),
		REQ_QTY decimal(18,2), available decimal(18,2), remainder decimal(18,2), ISSUED_QTY decimal(18,2), 
		QTY_ON_HAND decimal(18,2), QTY_IN_DEMAND decimal(18,2), CREATE_DATE datetime, Op_Se_No int, RESOURCE_ID nvarchar(30), 
		REQUIRED_DATE datetime)

	CREATE TABLE #Prev_Op_WODs (WO_op nvarchar(60), LOT_Op nvarchar(6), SPLIT_Op nvarchar(6), SUB_Op  nvarchar(6), 
		SEQ_NO_Op smallint, RESOURCE_ID nvarchar(30) NULL)
	
	/* Insert values into new temporal tables */
	INSERT INTO #RAW_MATERIAL_WODs
	SELECT distinct a.WORKORDER_BASE_ID, a.WORKORDER_LOT_ID, a.WORKORDER_SPLIT_ID, a.WORKORDER_SUB_ID, a.PART_ID, a.CALC_QTY, 
		iif(a.CALC_QTY <= b.QTY_ON_HAND, 0, 1) as 'available', iif(b.QTY_IN_DEMAND <= b.QTY_ON_HAND, 0, 1) as 'remainder', 
		a.ISSUED_QTY, b.QTY_ON_HAND, b.QTY_IN_DEMAND, convert(varchar (12), GETDATE(), 23) as Fecha_1, 
		OPERATION_SEQ_NO as 'Op_Se_No' ,  o.RESOURCE_ID, a.REQUIRED_DATE
	FROM REQUIREMENT a WITH (NOLOCK)  --//#VM: change from [SQL-LAB-1] to [SQL-LAB-2]
	INNER JOIN PART b WITH (NOLOCK) on a.PART_ID = b.ID  
	INNER JOIN OPERATION o on o.WORKORDER_BASE_ID=a.WORKORDER_BASE_ID and o.WORKORDER_LOT_ID=a.WORKORDER_LOT_ID and 
		o.WORKORDER_SPLIT_ID = a.WORKORDER_SPLIT_ID and o.SEQUENCE_NO = a.OPERATION_SEQ_NO
		and o.WORKORDER_SUB_ID = ISNULL(a.SUBORD_WO_SUB_ID, 0)
	INNER JOIN WORK_ORDER c WITH (NOLOCK) ON 
		a.WORKORDER_BASE_ID = c.BASE_ID and a.WORKORDER_LOT_ID = c.LOT_ID and a.WORKORDER_SPLIT_ID = c.SPLIT_ID
		
	WHERE c.STATUS not in ('X', 'C') and c.TYPE = 'W' and  o.RESOURCE_ID  = 'P2M1-RLSMTL'
	and (a.PART_ID = @Part_ID   or @Part_ID IS NULL   )
	--and a.WORKORDER_BASE_ID in ('1773899', '1762626', '1774463', '1771690')
	order by  a.REQUIRED_DATE , a.PART_ID, a.WORKORDER_BASE_ID, OPERATION_SEQ_NO,  o.RESOURCE_ID  asc
	;

	--select * from #RAW_MATERIAL_WODs where PART_ID = '70756E-8762 X 69.00'
	delete from #RAW_MATERIAL_WODs where ISSUED_QTY = REQ_QTY;

	WITH CTE AS (
		SELECT PART_ID, WO, REQ_QTY, QTY_ON_HAND AS INITIAL_QTY, --ISSUED_QTY,
			SUM(REQ_QTY) OVER (PARTITION BY PART_ID ORDER BY WO) AS 'CUMULATIVE_REST', 
			CASE 
				WHEN ISSUED_QTY = REQ_QTY THEN QTY_ON_HAND
				ELSE QTY_ON_HAND - SUM(REQ_QTY-ISSUED_QTY) OVER (PARTITION BY PART_ID ORDER BY REQUIRED_DATE) 
			END AS 'REMAINING_QTY'
		FROM #RAW_MATERIAL_WODs where --part_id = 'MS20257P5-7200' AND
		ISSUED_QTY < REQ_QTY --order by REQUIRED_DATE 
	)

	UPDATE R	/*  Updates inventory balances for each line  */
	SET R.remainder = 
			CASE 
				WHEN R.ISSUED_QTY = R.REQ_QTY THEN R.QTY_ON_HAND
				WHEN R.remainder < 0 THEN 0
			ELSE C.REMAINING_QTY END,
		QTY_ON_HAND = 
			CASE 
				WHEN C.REMAINING_QTY >= 0 THEN C.REMAINING_QTY  ELSE 0
			END,
		AVAILABLE = 
			CASE 
				WHEN C.REMAINING_QTY >= 0 THEN 0 ELSE 1
			END
	FROM #RAW_MATERIAL_WODs R
	JOIN CTE C ON R.PART_ID = C.PART_ID AND R.WO = C.WO 
	WHERE R.ISSUED_QTY < R.REQ_QTY 
				
	--select * from #RAW_MATERIAL_WODs where part_id = '70507P-2000 X 7.20 X 6.40' and ISSUED_QTY < REQ_QTY order by WO asc
	--select distinct TYPE from WORK_ORDER
	--SELECT * FROM #RAW_MATERIAL_WODs
	--SELECT * FROM #Prev_Op_WODs

	/*Step 1 insert into temp table #Prev_Op_WODs */
	INSERT INTO #Prev_Op_WODs (WO_op, LOT_Op, SPLIT_Op, SUB_Op, SEQ_NO_Op)
	SELECT o.WORKORDER_BASE_ID as 'WO_Op', o.WORKORDER_LOT_ID as 'Lot_Op', 
		o.WORKORDER_SPLIT_ID 'Split_Op', o.WORKORDER_SUB_ID as 'SubID_Op', 
		MIN(o.SEQUENCE_NO) as 'Seq_No'
	FROM OPERATION o with (NOLOCK) 
	INNER JOIN WORK_ORDER w  with (NOLOCK) on o.WORKORDER_BASE_ID = w.BASE_ID 
		and o.WORKORDER_LOT_ID = w.LOT_ID and o.WORKORDER_SPLIT_ID = w.SPLIT_ID 
		and o.WORKORDER_SUB_ID = w.SUB_ID
	WHERE w.STATUS = 'R' and o.STATUS = 'C' and o.COMPLETED_QTY > 0 and o.COMPLETED_QTY < o.CALC_START_QTY 
	group by o.WORKORDER_BASE_ID, o.WORKORDER_LOT_ID, o.WORKORDER_SPLIT_ID, 
		o.WORKORDER_SPLIT_ID, o.WORKORDER_SUB_ID 
	order by WORKORDER_BASE_ID

	/* Step 2 update ResourceID for temp table #Prev_Op_WODs */
	UPDATE b set b.RESOURCE_ID = a.RESOURCE_ID
	FROM OPERATION a  with (NOLOCK) 
	INNER JOIN #Prev_Op_WODs b with (NOLOCK) on a.WORKORDER_BASE_ID = b.WO_op 
		and a.WORKORDER_LOT_ID = b.LOT_Op and a.WORKORDER_SPLIT_ID = b.SPLIT_Op 
		and a.SEQUENCE_NO = b.SEQ_NO_Op
	--SELECT * FROM #Prev_Op_WODs


	--/* Main query original source WODs */
	--truncate table WODS_Output_Complement;
	--select 1 from #WODS_Output_Complement

	insert into #WODS_Output_Complement --#VM WODS Table with complements
	(
	[BASE_ID]
      ,[LOT_ID]
      ,[SPLIT_ID]
      ,[SUB_ID]
      ,[TYPE]
      ,[PART_ID]
      ,[WONUM]
      ,[DESIRED_QTY]
      ,[STATUS]
      ,[CUSTOMER_ORDER]
      ,[LINE_NO]
      ,[CUSTOMER_ID]
      ,[allocation_type]
      ,[CurrentOperation]
      ,[StatusCurrOp]
      ,[PRINTED_DATE]
      ,[DESIRED_RLS_DATE]
      ,[CREATE_DATE]
      ,[remaining_operations]
      ,[QTY_ON_HAND]
      ,[QTY_IN_DEMAND]
      ,[BUYER_USER_ID]
      ,[PLANNER_USER_ID]
      ,[COMMODITY_CODE]
      ,[DESCRIPTION]
      ,[DESIRED_WANT_DATE]
      ,[EXP/FLT]
      ,[user_10]
      ,[col_user_1]
      ,[RWPart]
      ,[CUSTOMER_PO_REF]
      ,[WORK_ORDER_NOTES]
      ,[CUST_ORDER_NOTATION]
      ,[CUST_ORD_CREATEDATE]
      ,[PartMaterialType]
      ,[MaterialType]
      ,[Alloy]
      ,[CO_AMOUNT]
      ,[UNIT_PRICE]
      ,[TOTAL_AMT_SHIPPED]
      ,[COL_AMOUNT]
      ,[RESOURCE_ID_Raw]
      ,[OPERATION_TYPE]
      ,[StatusCurrOpType]
      ,[CURROPCHK]
      ,[RESOURCE_ID]
      ,[AubPriText]
      ,[AubTcText]
      ,[HasAubPri]
      ,[HasAubTc]
      ,[TimeLimit]
      ,[LAST_CLOCK_OUT]
      ,[last_worked_seq]
      ,[last_clocked]
      ,[LATE]
      ,[LATEP2]
      ,[LATEP1]
      ,[LATEP3]
      ,[LATEBP1]
      ,[WAIT_DAYS]
      ,[EMPLOYEE_ID]
      ,[OPERATOR]
      ,[USER_1]
      ,[LEAD_SUPERVISOR]
      ,[SupervisorName]
      ,[StatusCurrOpMsg]
      ,[tdesc]
      ,[LABOR_TICKET_DESC]
      ,[BUYER]
      ,[BUYERFILTER]
      ,[SALESREP_ID]
      ,[Account]
      ,[Plant_ID]
      ,[Tooling]
      ,[IsAP1]
      ,[IsAP1a]
      ,[IsAP2]
      ,[IsAP2a]
      ,[IsAP3]
      ,[IsAP3a]
      ,[IsBP1]
      ,[IsUndetermined]
      ,[IsNORGRU]
      ,[IsTWMETA]
      ,[IsAMTRIB]
      ,[IsAUBMASK]
      ,[IsAUBPrime]
      ,[IsAUBSand]
      ,[IsAUBsetup]
      ,[IsAUBTC]
      ,[IsAUBtakedown]
      ,[IsAUBPartMark]
      ,[IsAUBFinalInspection]
      ,[IsAUBInspection]
      ,[IsAUBPenetrant]
      ,[IsAUBChemline]
      ,[AP1_ETRAC]
      ,[AP2_ETRAC]
      ,[AP3_ETRAC]
      ,[BP1_ETRAC]
      ,[AP1_PDEXP]
      ,[AP2_PDEXP]
      ,[AP3_PDEXP]
      ,[BP1_PDEXP]
      ,[AP1_FLT]
      ,[AP2_FLT]
      ,[AP3_FLT]
      ,[BP1_FLT]
      ,[AP1_Buyer_Joe]
      ,[AP1_Buyer_Rena]
      ,[AP1_Buyer_Tiffany]
      ,[AP1_Buyer_Sunni]
      ,[AP1_Buyer_Danielle]
      ,[AP1_Review]
      ,[AP1_PlanningQueue]
      ,[AP1_SkyFlex]
      ,[ID]
      ,[DESIRED_RECV_DATE]
      ,[SnapshotDate]
      ,[DEPARTMENT]
      ,[SUB_DEPARTMENT]
      ,[FACILITY]
      ,[REPT_DEPT]
      ,[PROCESS]
      ,[REPORT_GROUPING]
      ,[EMAIL_ADDR]
      ,[SETUP_INFO]
      ,[RLS_MT]
      ,[RM_READY]
      ,[remaining_operations_2]
      ,[P1F1_RecibedWO_Date]
	)

		
	SELECT a.BASE_ID, a.LOT_ID, a.SPLIT_ID, a.SUB_ID, a.TYPE, a.PART_ID, a.WONUM, a.DESIRED_QTY, a.STATUS, 
		a.CUSTOMER_ORDER, a.LINE_NO, a.CUSTOMER_ID, a.allocation_type, a.CurrentOperation, a.StatusCurrOp, 
		a.PRINTED_DATE, a.DESIRED_RLS_DATE, a.CREATE_DATE, a.remaining_operations, a.QTY_ON_HAND, a.QTY_IN_DEMAND, 
		a.BUYER_USER_ID, a.PLANNER_USER_ID, a.COMMODITY_CODE, a.DESCRIPTION, a.DESIRED_WANT_DATE, a.[EXP/FLT], a.user_10, 
		a.col_user_1, a.RWPart, a.CUSTOMER_PO_REF, a.WORK_ORDER_NOTES, a.CUST_ORDER_NOTATION, CUST_ORD_CREATEDATE, 
		a.PartMaterialType, a.MaterialType, a.Alloy, a.CO_AMOUNT, a.UNIT_PRICE, a.TOTAL_AMT_SHIPPED, a.COL_AMOUNT,
		/* patch WO with diferent CurrentOperation (LabTicket put to zero in closed month) */
		CASE --WHEN BASE_ID = '1736167' THEN b.RESOURCE_ID 
			WHEN BASE_ID = '1747844' THEN b.RESOURCE_ID ELSE a.RESOURCE_ID_Raw
		END as 'RESOURCE_ID_Raw',
		CASE --WHEN BASE_ID = '1736167' THEN b.OPERATION_TYPE 
			WHEN BASE_ID = '1747844' THEN c.OPERATION_TYPE ELSE a.OPERATION_TYPE
		END as 'OPERATION_TYPE',
		a.StatusCurrOpType, 
		CASE --WHEN BASE_ID = '1736167' THEN b.SEQ_NO 
			WHEN BASE_ID = '1747844' THEN c.SEQ_NO ELSE a.CURROPCHK
		END as 'CURROPCHK',
		CASE --WHEN BASE_ID = '1736167' THEN b.RESOURCE_ID 
			WHEN BASE_ID = '1747844' THEN c.RESOURCE_ID ELSE a.RESOURCE_ID
		END as 'RESOURCE_ID',
			--a.RESOURCE_ID_Raw, a.OPERATION_TYPE, a.StatusCurrOpType, a.CURROPCHK, a.RESOURCE_ID,
		--a.AubPriText, a.AubTcText, 
		/*	Update March-05--2025 Requested by Monica, replace a.AubPriText, a.AubTcText for Operation type Description	*/
		(	SELECT --distinct o.WORKORDER_BASE_ID, o.SEQUENCE_NO as 'Seq_No', o.RESOURCE_ID, o.OPERATION_TYPE, 
				distinct p.DESCRIPTION as 'OP_Description'
			FROM OPERATION o with (nolock)
			INNER JOIN OPERATION_TYPE p with (nolock) ON o.RESOURCE_ID = p.RESOURCE_ID and o.OPERATION_TYPE = p.ID
			where o.WORKORDER_BASE_ID = a.BASE_ID and o.STATUS not in ('X', 'C') and o.RESOURCE_ID like '%PNT-PRIME'
				and o.SEQUENCE_NO = ( SELECT min(b.SEQUENCE_NO) FROM OPERATION b where b.WORKORDER_BASE_ID = a.BASE_ID 
				and b.STATUS not in ('X', 'C') and b.RESOURCE_ID like '%PNT-PRIME' and b.SEQUENCE_NO > a.StatusCurrOp )
		) as 'AubPriText',
		(	SELECT --distinct o.WORKORDER_BASE_ID, o.SEQUENCE_NO as 'Seq_No', o.RESOURCE_ID, o.OPERATION_TYPE, 
				distinct p.DESCRIPTION as 'OP_Description'
			FROM OPERATION o with (nolock)
			INNER JOIN OPERATION_TYPE p with (nolock) ON o.RESOURCE_ID = p.RESOURCE_ID and o.OPERATION_TYPE = p.ID
			where o.WORKORDER_BASE_ID = a.BASE_ID and o.STATUS not in ('X', 'C') and o.RESOURCE_ID like '%PNT-TC'
				and o.SEQUENCE_NO = ( SELECT min(b.SEQUENCE_NO) FROM OPERATION b where b.WORKORDER_BASE_ID = a.BASE_ID 
				and b.STATUS not in ('X', 'C') and b.RESOURCE_ID like '%PNT-TC' and b.SEQUENCE_NO > a.StatusCurrOp )	
		) as 'AubTcText',
		--a.HasAubPri, 
		case when EXISTS(
			SELECT distinct p.DESCRIPTION as 'OP_Description'
			FROM OPERATION o with (nolock)
			INNER JOIN OPERATION_TYPE p with (nolock) ON o.RESOURCE_ID = p.RESOURCE_ID and o.OPERATION_TYPE = p.ID
			where o.WORKORDER_BASE_ID = a.BASE_ID and o.STATUS not in ('X', 'C') and o.RESOURCE_ID like '%PNT-PRIME'
				and o.SEQUENCE_NO = ( SELECT min(b.SEQUENCE_NO) FROM OPERATION b where b.WORKORDER_BASE_ID = a.BASE_ID 
				and b.STATUS not in ('X', 'C') and b.RESOURCE_ID like '%PNT-PRIME' and b.SEQUENCE_NO > a.StatusCurrOp )
			) then 1 
		else 0 end as 'HasAubPri',
		--a.HasAubTc, 
		case when EXISTS(
			SELECT distinct p.DESCRIPTION as 'OP_Description'
			FROM OPERATION o with (nolock)
			INNER JOIN OPERATION_TYPE p with (nolock) ON o.RESOURCE_ID = p.RESOURCE_ID and o.OPERATION_TYPE = p.ID
			where o.WORKORDER_BASE_ID = a.BASE_ID and o.STATUS not in ('X', 'C') and o.RESOURCE_ID like '%PNT-TC'
				and o.SEQUENCE_NO = ( SELECT min(b.SEQUENCE_NO) FROM OPERATION b where b.WORKORDER_BASE_ID = a.BASE_ID 
				and b.STATUS not in ('X', 'C') and b.RESOURCE_ID like '%PNT-TC' and b.SEQUENCE_NO > a.StatusCurrOp )
			) then 1 
		else 0 end as 'HasAubTc',
		a.TimeLimit, a.LAST_CLOCK_OUT, 
		a.last_worked_seq, a.last_clocked, a.LATE, a.LATEP2, 
		a.LATEP1, a.LATEP3, a.LATEBP1, a.WAIT_DAYS, a.EMPLOYEE_ID, 
		iif(a.OPERATOR = 'Eric Diaz', 'Greg Berntsen', a.OPERATOR) as 'OPERATOR', a.USER_1, 
		iif(a.LEAD_SUPERVISOR = 'AP1-Eric Diaz', 'AP1-Greg Berntsen', a.LEAD_SUPERVISOR) as 'LEAD_SUPERVISOR', 
		iif(a.SupervisorName = 'Eric Diaz', 'Greg Berntsen', a.SupervisorName) as 'SupervisorName', 
		a.StatusCurrOpMsg, a.tdesc, a.LABOR_TICKET_DESC, a.BUYER, a.BUYERFILTER, a.SALESREP_ID, a.Account, 
		a.Plant_ID, a.Tooling, 
		a.IsAP1, IIF(a.Plant_ID = 'AP1', 1, a.IsAP1) as 'IsAP1a', 
		a.IsAP2, IIF(a.Plant_ID = 'AP2', 1, a.IsAP2) as 'IsAP2a', 
		a.IsAP3, IIF(a.Plant_ID = 'AP3', 1, a.IsAP3) as 'IsAP3a', 
		a.IsBP1, a.IsUndetermined, a.IsNORGRU, a.IsTWMETA, a.IsAMTRIB, a.IsAUBMASK, 
		a.IsAUBPrime, a.IsAUBSand, a.IsAUBsetup, a.IsAUBTC, a.IsAUBtakedown, a.IsAUBPartMark, a.IsAUBFinalInspection, 
		a.IsAUBInspection, a.IsAUBPenetrant, a.IsAUBChemline, a.AP1_ETRAC, a.AP2_ETRAC, a.AP3_ETRAC, a.BP1_ETRAC, AP1_PDEXP, 
		a.AP2_PDEXP, a.AP3_PDEXP, a.BP1_PDEXP, a.AP1_FLT, a.AP2_FLT, a.AP3_FLT, a.BP1_FLT, a.AP1_Buyer_Joe, a.AP1_Buyer_Rena, 
		a.AP1_Buyer_Tiffany, a.AP1_Buyer_Sunni, a.AP1_Buyer_Danielle, a.AP1_Review, a.AP1_PlanningQueue, a.AP1_SkyFlex, a.ID, 
		a.DESIRED_RECV_DATE, a.SnapshotDate, a.DEPARTMENT, a.SUB_DEPARTMENT, a.FACILITY, a.REPT_DEPT, a.PROCESS, a.REPORT_GROUPING, 
		a.EMAIL_ADDR, a.SETUP_INFO
		/* Ad new column to check raw material available */
		, case when a.remaining_operations like '%P2M1-RLSMTL%' then 'P2M1-RLSMTL' 
			when a.remaining_operations like '%P2M1-KIT-FG%' then 'P2M1-KIT-FG' 
			else 'NO' end as 'RLS_MT'
		/*  evaluate inventory into WO just to WO discard material issued */
		-- ~22
		--          --> 1.00    -->  0.00    -- > 24.00
		, case when available = 0 and r.ISSUED_QTY < r.REQ_QTY then 'YES' 
				when available > 0 then 'NO'
				when available = 0 and r.ISSUED_QTY = r.REQ_QTY then NULL
		else NULL end AS 'RM_READY'  
		, a.remaining_operations as 'remaining_operations_2', e.P1F1_RecibedWO_Date

	FROM [SQL-LAB-1].LIVESupplemental.dbo.WODS_output_ETL a WITH (NOLOCK) 
	left outer join #Prev_Op_WODs b on a.BASE_ID = b.WO_op and a.LOT_ID = b.LOT_Op 
		and a.SPLIT_ID = b.SPLIT_Op and a.SUB_ID = b.SUB_Op

	/*join to patch WO with diferent CurrentOperation (LabTicket put to zero in closed month) */
	left join ( 
		SELECT WORKORDER_BASE_ID as 'WO', WORKORDER_LOT_ID as 'Lot', WORKORDER_SPLIT_ID as 'Split', 
			RESOURCE_ID, SEQ_NO, OPERATION_TYPE 
		FROM OPERATION O	
		inner join (SELECT min(SEQUENCE_NO) as 'SEQ_NO'
			FROM OPERATION with (nolock) WHERE WORKORDER_BASE_ID IN ('1747844')
			AND RUN_HRS > 0 and COMPLETED_QTY = 0 and status = 'R'
		) p on o.SEQUENCE_NO = p.SEQ_NO
		--WHERE WORKORDER_BASE_ID IN ('1747844') AND WORKORDER_LOT_ID = '1' AND WORKORDER_SPLIT_ID = '0' 
			AND RUN_HRS > 0 and COMPLETED_QTY = 0 and status = 'R'  
	) c ON a.BASE_ID = c.WO and a.LOT_ID = c.Lot and a.SPLIT_ID = c.Split

	/* P1F1_RecibedWO_Date */
	LEFT OUTER JOIN ( 
		select WORKORDER_BASE_ID, WORKORDER_LOT_ID, WORKORDER_SPLIT_ID, WORKORDER_SUB_ID, 
			min( convert(varchar, SHIFT_DATE, 1) ) as 'P1F1_RecibedWO_Date' 
		from [SQL-LAB-1].LIVE.dbo.LABOR_TICKET where RESOURCE_ID = 'P1F1-REC'
		group by WORKORDER_BASE_ID, WORKORDER_LOT_ID, WORKORDER_SPLIT_ID, WORKORDER_SUB_ID 
	) e ON a.BASE_ID = e.WORKORDER_BASE_ID and a.LOT_ID = e.WORKORDER_LOT_ID 
		and a.SPLIT_ID = e.WORKORDER_SPLIT_ID and a.SUB_ID = e.WORKORDER_SUB_ID
		
	/*Join to add Raw Material*/
	LEFT JOIN (
		SELECT WO, LOT, SPLIT, SUM(available) as 'available', 
			SUM(REQ_QTY) as 'REQ_QTY', SUM(ISSUED_QTY) as 'ISSUED_QTY'
		FROM #RAW_MATERIAL_WODs
		group by WO, LOT, SPLIT
	) r ON r.WO = a.BASE_ID and a.LOT_ID = r.LOT and a.SPLIT_ID = r.SPLIT 
			

	where a.BASE_ID = @wo  -- '1740806'
		--and RM_READY is not null


	-- select HasAubPri, HasAubTc, * from [DataWarehouse].[dbo].[WODS_Output_Complement] where base_id = '1771720'
		
	/*  Timelimit */
	UPDATE A SET A.TimeLimit = IIF(UDF.BOOL_VAL IS NULL, 0, UDF.BOOL_VAL) 
	--select A.BASE_ID, A.CurrentOperation, A.TimeLimit, WO.WO_PK
	--, IIF(UDF.BOOL_VAL IS NULL, 0, UDF.BOOL_VAL)
	FROM #WODS_Output_Complement A
	INNER JOIN (
		SELECT WORKORDER_BASE_ID AS 'BASE_ID', WORKORDER_LOT_ID AS 'LOT_ID', WORKORDER_SPLIT_ID AS 'SPLIT_ID', 
		WORKORDER_SUB_ID AS 'SUB_ID', SEQUENCE_NO,
		'W~'+WORKORDER_BASE_ID+'~'+
		CONVERT(VARCHAR(12), WORKORDER_SPLIT_ID)+'~'+
		CONVERT(VARCHAR(12), WORKORDER_LOT_ID)+'~'+
		--CONVERT(VARCHAR(12), WORKORDER_SPLIT_ID)+'~'+
		CONVERT(VARCHAR(12), WORKORDER_SUB_ID)+'~'+
		CONVERT(VARCHAR(12), SEQUENCE_NO) AS 'WO_PK'
		FROM OPERATION WITH (NOLOCK) WHERE WORKORDER_TYPE = 'W' 
	) AS WO ON A.BASE_ID = WO.BASE_ID AND A.LOT_ID = WO.LOT_ID AND A.SPLIT_ID = WO.SPLIT_ID 
		AND A.SUB_ID = WO.SUB_ID AND A.CurrentOperation = WO.SEQUENCE_NO
	left join (
		SELECT DOCUMENT_ID, BOOL_VAL FROM USER_DEF_FIELDS UDF
		WHERE PROGRAM_ID = N'VMMFGWIN_OP' AND UDF.ID = N'UDF-0000048' AND DOCUMENT_ID LIKE 'W%'
	) UDF ON WO.WO_PK = UDF.DOCUMENT_ID
	WHERE A.BASE_ID = @wo -- '1782127'
	;

	
--	/*		EXEC SP_WODS_Complement		*/
--RETURN;
--GO

--SELECT  * FROM #WODS_Output_Complement;
select * FROM #RAW_MATERIAL_WODs
WHERE 1=1
AND (WO = @wo or @wo is null)

	SELECT distinct a.WORKORDER_BASE_ID
	--, a.WORKORDER_LOT_ID, a.WORKORDER_SPLIT_ID, a.WORKORDER_SUB_ID
	, a.PART_ID, a.CALC_QTY, 
		iif(a.CALC_QTY <= b.QTY_ON_HAND, 0, 1) as 'available', iif(b.QTY_IN_DEMAND <= b.QTY_ON_HAND, 0, 1) as 'remainder', 
		a.ISSUED_QTY, b.QTY_ON_HAND, b.QTY_IN_DEMAND, convert(varchar (12), GETDATE(), 23) as Fecha_1, 
		OPERATION_SEQ_NO as 'Op_Se_No' ,  o.RESOURCE_ID, a.REQUIRED_DATE
		into #results
	FROM REQUIREMENT a WITH (NOLOCK)  --//#VM: change from [SQL-LAB-1] to [SQL-LAB-2]
	INNER JOIN PART b WITH (NOLOCK) on a.PART_ID = b.ID  
	INNER JOIN OPERATION o on o.WORKORDER_BASE_ID=a.WORKORDER_BASE_ID and o.WORKORDER_LOT_ID=a.WORKORDER_LOT_ID and 
		o.WORKORDER_SPLIT_ID = a.WORKORDER_SPLIT_ID and o.SEQUENCE_NO = a.OPERATION_SEQ_NO
		and o.WORKORDER_SUB_ID = ISNULL(a.SUBORD_WO_SUB_ID, 0)
	INNER JOIN WORK_ORDER c WITH (NOLOCK) ON 
		a.WORKORDER_BASE_ID = c.BASE_ID and a.WORKORDER_LOT_ID = c.LOT_ID and a.WORKORDER_SPLIT_ID = c.SPLIT_ID
		
	WHERE 1=1
		and (a.PART_ID = @Part_ID   or @Part_ID IS NULL   )
	
	AND c.STATUS not in ('X', 'C') and c.TYPE = 'W' and  o.RESOURCE_ID  = 'P2M1-RLSMTL'
	and 
	  ( a.WORKORDER_BASE_ID = @WO or @wo is null)					------in ('1773899', '1762626', '1774463', '1771690')
	order by  a.REQUIRED_DATE , a.PART_ID, a.WORKORDER_BASE_ID, OPERATION_SEQ_NO,  o.RESOURCE_ID  asc;

	-- inventory transactions returns

	
SELECT DISTINCT  
'summary - issue release' note
 --WORKORDER_BASE_ID
,max(WORKORDER_BASE_ID) MAX_WORKORDER_BASE_ID
,MIN(WORKORDER_BASE_ID) MIN_WORKORDER_BASE_ID
,   i.TYPE,     CLASS, status
,     COUNT(*) as Count
,    MIN(TRANSACTION_DATE) as Earliest,    MAX(TRANSACTION_DATE) as Latest
,CASE     -- Issue Returns   
WHEN i.TYPE = 'IR' AND CLASS = 'R' THEN 'Issue Return - Material Returned to Stock'    
WHEN i.TYPE = 'I' AND CLASS = 'R' THEN 'Issue Return - General'        -- Receipt Returns      
WHEN i.TYPE = 'RR' AND CLASS = 'R' THEN 'Receipt Return - WO Receipt Reversed'    
WHEN i.TYPE = 'R' AND CLASS = 'R' THEN 'Receipt Return - General'        -- Normal Issues   
WHEN i.TYPE = 'I' AND CLASS = 'M' THEN 'Issue to Manufacturing/Work Order'    
WHEN i.TYPE = 'I' AND CLASS = 'S' THEN 'Issue for Sales/Shipping'   
WHEN i.TYPE = 'I' AND CLASS = 'N' THEN 'Issue - Normal'        -- Normal Receipts   
WHEN i.TYPE = 'R' AND CLASS = 'P' THEN 'Receipt from Purchase Order'   
WHEN i.TYPE = 'R' AND CLASS = 'M' THEN 'Receipt from Manufacturing/Work Order'    
WHEN i.TYPE = 'R' AND CLASS = 'N' THEN 'Receipt - Normal'        -- Adjustments    
WHEN i.TYPE = 'A' AND CLASS = 'A' THEN 'Inventory Adjustment'   
WHEN i.TYPE = 'A' AND CLASS = 'C' THEN 'Cycle Count Adjustment'    
WHEN i.TYPE = 'A' AND CLASS = 'P' THEN 'Physical Inventory Adjustment'        -- Transfers    
WHEN i.TYPE = 'T' AND CLASS = 'N' THEN 'Location/Warehouse Transfer'        -- Standalone types (when CLASS might be NULL or not specified)   
WHEN i.TYPE = 'IR' THEN 'Issue Return'    
WHEN i.TYPE = 'RR' THEN 'Receipt Return'    
WHEN i.TYPE = 'I' THEN 'Issue'    
WHEN i.TYPE = 'R' THEN 'Receipt'    
WHEN i.TYPE = 'A' THEN 'Adjustment'    
WHEN i.TYPE = 'T' THEN 'Transfer'        -- Catch-all    
   ELSE i.TYPE + ' - ' + ISNULL(CLASS, 'N/A')
   END as TRANSACTION_TYPE_DESCRIPTION
FROM INVENTORY_TRANS i (nolock)

  inner 
  join dbo.WORK_ORDER a
  on i.WORKORDER_BASE_ID=a.BASE_ID
    and i.WORKORDER_LOT_ID=a.LOT_ID and
    i.WORKORDER_SPLIT_ID = a.SPLIT_ID


WHERE TRANSACTION_DATE >= DATEADD(MONTH, -6, GETDATE())
and WORKORDER_BASE_ID in (select WORKORDER_BASE_ID FROM work_order)
GROUP BY I.TYPE, CLASS, [STATUS] 
ORDER BY I.TYPE, CLASS;

select *
 FROM INVENTORY_TRANS i (nolock)
where WORKORDER_BASE_ID = '1670717'