--- Report.usp_Report_Indented_BOM
---
USE [LIVE]
GO

/****** Object:  StoredProcedure [report].[usp_Report_Indented_BOM]    Script Date: 4/21/2026 11:41:52 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS

-- C:\SQL\Uber Query\1.3 BOM\BOM.02.30 Whereused - Report.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.02.40 Whereused - Report.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.02.41 Whereused - Report.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.02.42 Whereused - Report.sql
-- C:\SQL\Uber Query\1.3 BOM\BOMTruncate table #bom Whereused - Report.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.04.40 Indented BOM.2.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.04.40 Indented BOM.3.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.04.40 Indented BOM.4.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.04.40 Indented BOM.6.sql
-- C:\SQL\Uber Query\1.3 BOM\BOM.04.40 Indented BOM.7.sql

/**********************************************************************************************
description:	where used - the parents for a component
sample:			returns all parents of a part #. if end item then just the end item.
date        modified by         change description
----------  ------------------  ------------------------------------------------------------
02/13/2020	william thompson	created.
02/17/2020	william thompson	updated - where used set, #sourcedparts
02/17/2020	william thompson	test - parent part search.
02/17/2020	william	thompson	union isnotarequirent with isarequirement
03/05/2020  Willism Thompson	correct for SUBORD_WO_SUB_ID and legs level 0
03/10/2020  William Thompson	Test Plan 2020-03-10.3 - >
03/10/2020  William Thompson	Test Plan 2020-03-10.5 - > 2.43 removed join to subord_wo_sub_id, updated sort
03/10/2020  William Thompson	operation_seq_no added to select
03/11/2020  William Thompson	added    , status nchar(1), qty_per decimal(15,8), calc_qty decimal(14,4)
03/12/2020	William Thompson	sort order is recomputing for multilevel, e.g. BACR15BA3AD5R5C-CMP child of 287T1034-983
03/12/2020.2	William Thompson	problem when 453T1450-9013 is input into the search BOM. two lines for 20243C-063 CMP
03/12/2020.3	William Thompson	The child component dataset was updated to exclude top-level components; for .2
05/15/2020  William Thompson    Two passes - 1 for legs, 1 for non legs
05/15/2020.2  William Thompson	update to use while loop
06/03/2020.1  William Thompson  test passea because parent has eng mstr; bom 151W7573-7
06/03/2020.1  William Thompson    -- cont'd -- parent  L2:  478W8702-50 in bom  151W7573-7
06/04/2020	William Thompson	implemnted join to part_site; parents must have eng mstr
06/06/2020  William Thompson	Usage_Um added
06/06/2020	William Thompson	Level2 was added for fact relational data integrity
06/06/2020.2  William Thompson  part path level2 = 2 prepends '1-' as all legs level 1
06/09/2020	William Thompson	pn 453T1450-9073 has two records in masters, eng-mstr-0 and eng-mstr-1
06/09/2020	William Thompson	pn 453T1450-9073 fixed join to part site (components pass 2 with no eng master coalesce to 0)
06/10/2020  William Thompson	pn 151W7573-7

TESTING
=======================
2020-06-10   -- > BOM  -- > 453T1450-9073 has a leg component
2020-06-04.2 -- > BOM.6  -- >   411T3484-64B	-- > part has three legs
2020-06-04.1 Test Plan	-- > Test File  -- > Part in test:  - - > Desc
-- Test 2020-05-93 --------------------------------------
-- Test Passes because level to part '478W8702-50' can parent; this is bom for '151W7573-7'
   151W7573-7  ** Has a level 3
   - L1:  478W8710-18
   - L2:  478W8702-50   << ------
   - L3:  6AL4V-063 24 X 36 .063 
-- 2  ////  
--------------------------------------

2020-05-27.1  -- > BOM.4    -- > 151W1583-3    -- > Defect; bringing in 6AL4V-1875 not in BOM
2020-03-10.4  -- > BOM.02.41  -- >  4391B1867-1   - - > part with leg.
2020-03-10-.3 -- > BOM.02.42  -- >  140W9616-9521B - - > part with lot card 1
2020-03-10.5   -- > BOM.02.43  -->  411T3484-64B	-- > part has three legs
Test Plan 1.6  -- > BOM.02.44  -- > 32-901-08-01  -- > multilevel part
Test Plan 1.3  -- > BOM.02.45	--> 287A4131-66  -- > this is a problem, won't print in BOM (in EngMf menu)

Tester:

Legs:
select * from work_order w
where part_id in(
		select w.part_id from work_order w
		where (1=1)
		and part_id = base_id
		and w.type = 'M'
		--and part_id = '453T1450-15'
)
--and create_Date > '2020-01-01'
and sub_id > 0
order by w.type, base_id

*********************************************************************************************/


-- Exec Report.usp_Report_Indented_BOM @dwBomName = '287U0068-9761' --'453T1450-9073' -- '151W7573-7' -- '411T3484-64B'   -- '255U0183-3'   
-- '453T1450-15'  '453T1450-9013'  -- '453T1450-19'  --'255U0183-3' -- '453T1450-9013'   -- '453T1450-9017' -- '20243C-063 CMP' --'255U0193-2'  -- '284T4224-1'  --'146T5500-114'  --'287T1034-983' -- '411T3484-64B' --'140W9616-9521B' -- '32-901-08-01' --  '4391B1867-1'  --  '151W0231-24'  -- --'32-901-08-01'  '32-910-01-06-proto' '74A588133-2009'  ,'151W0231-3'   ,'151W0231-3'  ,'151W0231-2', '100T1430-87', '151W0231-24', '6AL4VE-1278', '151W0231-2'
-- create schema report
CREATE proc [report].[usp_Report_Indented_BOM]

 --declare 
 @dwBomName nvarchar(30) = '' --'74A588133-1009'  -- '453T1450-9073' -- '4391B1867-1'  ---'411T3484-64B' -- '411T3484-64B'  -- '151W7573-7' -- '151W7573-7'  -- '453T1450-9073' -- '411T3484-64B' -- = '74A588133-1009'   --  '151W1583-3'  -- '74A588133-1009'  -- '151W1583-3'  -- '255U0183-3' 
as

set transaction isolation level read uncommitted
set deadlock_priority low
-- set nocount off
set nocount on

IF OBJECT_ID('tempdb..#bom') IS NOT NULL DROP TABLE #bom 
if object_id('tempdb..#results') is not null drop table #results
if object_id('tempdb..#parents') is not null drop table #parents
if object_id('tempdb..#children') is not null drop table #children
if object_id('tempdb..#indentbom') is not null drop table #indentbom

if object_id('tempdb..#passX') is not null drop table #passX

if object_id('tempdb..#Legs_Set') is not null drop table #Legs_Set
if object_id('tempdb..#Legs_Dependent_Set') is not null drop table #Legs_Dependent_Set

if object_id('tempdb..#Pass2_parents') is not null drop table #Pass2_parents
if object_id('tempdb..#Pass2_children') is not null drop table #Pass2_children
if object_id('tempdb..#noReqs') is not null drop table #noReqs

if object_id('tempdb..#temp1') is not null drop table #temp1
if object_id('tempdb..#temp2') is not null drop table #temp2
if object_id('tempdb..#temp3') is not null drop table #temp3

PRINT 'Time: ' +  CONVERT(VARCHAR(MAX),getdate())
-- select * from #temp1
-- select * from #temp2 where part_id = '6AL4V-187 2.21 x 4.48'
-- select * from #temp2 where base_id = '6AL4V-187 2.21 x 4.48'
-- select * from #temp2 where part_id = '6AL4V-1875'
-- select * from #temp2 where base_id = '6AL4V-1875'
--select * from WORK_ORDER where type = 'M' and BASE_ID = '151W1583-3'
--select * from WORK_ORDER where part_id = '6AL4V-187 2.21 x 4.48'
--select * from WORK_ORDER where part_id = '6AL4V-1875'
--End Item: '151W1583-3'
--Component: '6AL4V-187 2.21 x 4.48'
--Defect: '6AL4V-1875'
--select * from part where id = '6AL4V-1875'
-- _Temp991 Testing BOM Seq and Pc


-- declarations
-- ~~
declare @RowCountParents2 int = 0
declare @RowCountParents1 int = 0
DECLARE @execution_id NVARCHAR(30)

-- Testing, comment out following for prod

Declare @dwIdx int
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS

-- temp tables ----------------------------------------
--
--
-- ----------------------------------------------------

create table #bom(
	--type nchar(1) null,
	base_id nvarchar(30) null,
	lot_id nvarchar(3) null,
	split_id nvarchar(3) null,
	sub_id nvarchar(3) null,
	operation_seq_no smallint null,
	piece_no smallint null,
	subord_wo_sub_id nvarchar(3) null,
	part_id nvarchar(30) null,
	dwidx int null,
	dwbomname nvarchar(30) null,
	dwbomid nvarchar(90) null,
	level int null,
	tab int null,
	partpath nvarchar(30) null,
	sortx decimal(16, 10) null,
	depth int null,
	up_level_part_id nvarchar(30) null,
	comment nvarchar(30) null,

	[status]  nchar(1),
    qty_per decimal(15,8),
    calc_qty decimal(14,4),

	description nvarchar(50) null,

	[level2] int null,

	usage_um nvarChar(15)
)  

create table #results(
	type nchar(1) null,
	base_id nvarchar(30) null,
	lot_id nvarchar(3) null,
	split_id nvarchar(3) null,
	sub_id nvarchar(3) null,
	operation_seq_no smallint null,
	piece_no smallint null,
	subord_wo_sub_id nvarchar(3) null,
	part_id nvarchar(30) null,
	dwidx int null,
	dwbomname nvarchar(30) null,
	dwbomid nvarchar(90) null,
	level int null,
	tab int null,
	partpath nvarchar(30) null,
	sortx decimal(16, 10) null,
	depth int null,
	[status]  nchar(1),
    qty_per decimal(15,8),
    calc_qty decimal(14,4),

	description nvarchar(50) null,

	[level2] int null,
	usage_um nvarChar(15)
)

create table #children(
	type nchar(1) null,
	base_id nvarchar(30) null,
	lot_id nvarchar(3) null,
	split_id nvarchar(3) null,
	sub_id nvarchar(3) null,
	operation_seq_no smallint null,
	piece_no smallint null,
	subord_wo_sub_id nvarchar(3) null,
	part_id nvarchar(30) null,
	dwidx int null,
	dwbomname nvarchar(30) null,
	dwbomid nvarchar(90) null,
	level int null,
	tab int null,
	partpath nvarchar(30) null,
	sortx decimal(16, 10) null,
	depth int null,
	[status]  nchar(1),
    qty_per decimal(15,8),
    calc_qty decimal(14,4),

	description nvarchar(50) null,

	[level2] int null,
	usage_um nvarChar(15)
)


create table #parents(
	type nchar(1) null,
	base_id nvarchar(30) null,
	lot_id nvarchar(3) null,
	split_id nvarchar(3) null,
	sub_id nvarchar(3) null,
	operation_seq_no smallint null,
	piece_no smallint null,
	subord_wo_sub_id nvarchar(3) null,
	part_id nvarchar(30) null,
	dwidx int null,
	dwbomname nvarchar(30) null,
	dwbomid nvarchar(90) null,
	level int null,
	tab int null,
	partpath nvarchar(30) null,
	sortx decimal(16, 10) null,
	depth int null,
	[status]  nchar(1),
    qty_per decimal(15,8),
    calc_qty decimal(14,4),

	description nvarchar(50) null,

	[level2] int null,
	usage_um nvarChar(15)
)

create table #passX(
--	type nchar(1) null,
	base_id nvarchar(30) null,
	lot_id nvarchar(3) null,
	split_id nvarchar(3) null,
	sub_id nvarchar(3) null,
	operation_seq_no smallint null,
	piece_no smallint null,
	subord_wo_sub_id nvarchar(3) null,
	part_id nvarchar(30) null,
	dwidx int null,
	dwbomname nvarchar(30) null,
	dwbomid nvarchar(90) null,
	level int null,
	tab int null,
	partpath nvarchar(30) null,
	sortx decimal(16, 10) null,
	depth int null,

	up_level_part_id nvarchar(30) null,
	comment nvarchar(30) null,

	[status]  nchar(1),
    qty_per decimal(15,8),
    calc_qty decimal(14,4),

	description nvarchar(50) null,

	[level2] int null,

	usage_um nvarChar(15)

)  

-- exclude parts that are unplanned unless they are in requirements
create table #noReqs (part_id nvarchar(30))

-- ***** PART 1 ***********************************************


--select  
--  r.WORKORDER_TYPE, r.WORKORDER_BASE_ID, WORKORDER_SUB_ID, OPERATION_SEQ_NO, PIECE_NO
--  ,SUBORD_WO_SUB_ID, PART_ID

--from requirement r where (1=1) and workorder_type = 'M' and SUBORD_WO_SUB_ID  is null
--and WORKORDER_BASE_ID like '%'
--and WORKORDER_BASE_ID = '453T1450-9013' -- '287T1034-983'
--select * from requirement where workorder_base_id = part_id -- empty
-- 

--		select * from work_order w
--		where (1=1)
--		and part_id = base_id
--		and w.type = 'M'
--		and part_id = '287T1034-983'

--CREATE CLUSTERED INDEX Cidx_Child ON #children (base_id, lot_id, split_id, sub_id, part_id)

-- select * from #children where base_id = '453T1450-15'

--declare @P301 nvarchar(30) = 'M'
--  ,@P302 nvarchar(30) = '453T1450-9013'
--  ,@P303 nvarchar(30) = '0'
--  ,@P304 nvarchar(30) = '0'
--  ,@P305 nvarchar(30) = '1'  -- sub id


--SELECT RQ.OPERATION_SEQ_NO
--, RQ.PIECE_NO, RQ.PART_ID, RQ.SUBORD_WO_SUB_ID, RQ.QTY_PER, RQ.FIXED_QTY
--, RQ.SCRAP_PERCENT, RQ.DIMENSIONS, RQ.USAGE_UM, RQ.USER_1, RQ.USER_2, RQ.USER_3, RQ.USER_4, RQ.USER_5
--, RQ.USER_6, RQ.USER_7, RQ.USER_8, RQ.USER_9, RQ.USER_10, RQ.QTY_PER, RQ.WORKORDER_SUB_ID
--, RQ.WORKORDER_TYPE, RQ.WORKORDER_BASE_ID
--, RQ.WORKORDER_LOT_ID, RQ.WORKORDER_SPLIT_ID 
--FROM REQUIREMENT RQ 
--WHERE RQ.WORKORDER_TYPE = @P301 
--AND RQ.WORKORDER_BASE_ID = @P302 
--AND RQ.WORKORDER_LOT_ID = @P303 
--AND RQ.WORKORDER_SPLIT_ID = @P304 
--AND RQ.WORKORDER_SUB_ID = @P305 
--ORDER BY RQ.WORKORDER_TYPE, RQ.WORKORDER_BASE_ID
--, RQ.WORKORDER_LOT_ID, RQ.WORKORDER_SPLIT_ID, RQ.WORKORDER_SUB_ID, RQ.OPERATION_SEQ_NO, RQ.PIECE_NO
----',@p5 output,@p6 output,@p7 output,N'M',N'287T1034-983',N'0',N'0',N'1'
----select @p1, @p2, @p5, @p6, @p7

insert into #noReqs
--declare @dwBomName nvarchar(30) = null -- '287T1034-983'
	select

	  wo.part_id

	from work_order wo
	join part p
	on wo.part_id = p.id
	where wo.[type] = 'm'
	and (wo.part_id = @dwBomName
		or @dwBomName IS NULL)
	and wo.SUB_ID = 0
	and isnull(p.order_policy,'') = 'N'
	and not exists(
	 select 
	   x.part_id
	 from(
		select workorder_base_id part_id 
		from requirement 
		where workorder_type = 'M'
		union
		select part_id  
		from requirement 
		where workorder_type = 'M'
		) AS x
	 where x.part_id =wo.part_id
 )

 -- select * from #noreqs

-- ****** PART 2 ***********************************************

-- Cursor --------------------------------------
--
--
-- ---------------------------------------------
declare @counter int = 1
   , @MaxCount int = 1 -- 100000
set @counter = 1
set @MaxCount = 1

-- declare iterator and loop
BEGIN


------ ~~ pass 1
----DECLARE execution_cursor CURSOR LOCAL FOR 
----SELECT wo.part_id 
----FROM WORK_ORDER wo
----JOIN PART p
----ON wo.part_id = p.id
----WHERE wo.[TYPE] = 'm'
----and (wo.part_id = @dwBomName
----    or @dwBomName IS NULL)
----and wo.SUB_ID = 0
----and isnull(p.status,'') <> 'O'
------ update 2020-03-12 exclude unplanned unless they are in reqs
------and isnull(p.order_policy,'') <> 'N'
----and isnull(wo.part_id,'') not in (select part_id from #noReqs)

-- -------------------------------------------------------------- ~~
----~~
DECLARE @execution_process TABLE (execution_id  nvarchar(30) PRIMARY KEY)
--Here we declare an indexed table variable to store all the execution_ids
DECLARE @execution_process2 TABLE (execution_id  nvarchar(30) PRIMARY KEY)
--And here we declare a 2nd index table variable for 2nd iteration
 PRINT CONVERT(VARCHAR(MAX),GETDATE())
INSERT INTO  @execution_process2
	SELECT wo.part_id 
	FROM WORK_ORDER wo (nolock)
	JOIN PART p (nolock)
	ON wo.part_id = p.id 
  -- update 6/9/2020 - multiple eng_mstrs
    JOIN PART_SITE ps
	ON wo.part_id = ps.PART_ID
	and ps.SITE_ID	= 'sk01'
	and wo.lot_id = ps.ENGINEERING_MSTR

	WHERE wo.[TYPE] = 'm'
	and (wo.part_id = @dwBomName
		or @dwBomName IS NULL)
	and wo.SUB_ID = 0
	and isnull(p.status,'') <> 'O'
	and isnull(wo.part_id,'') not in (select part_id from #noReqs)
--Here we insert all our ids into the variable/temporary table

-- copy @execution_process to @execution_process2 for another iteration

delete from @execution_process
insert into @execution_process
select * from @execution_process2

select *
INTO #TEMP3
FROM @execution_process


--SELECT * FROM #TEMP3

--- ~~ pass 1
Truncate table #bom
--OPEN execution_cursor
--FETCH NEXT FROM execution_cursor INTO @execution_id
            
--WHILE @@FETCH_STATUS = 0
-- PASS 1 ~~
PRINT CONVERT(VARCHAR(MAX),GETDATE())
WHILE EXISTS	(SELECT execution_id  FROM @execution_process)
--This is a basic WHILE loop that runs as long as there is data in the variable table

BEGIN
                        
    BEGIN TRY
	------ Execution of Code begins here:  *** wnt
	------ ---------------------------------------------
	------ ****** 
	------ ---------------------------------------------
	----	-- Execution of Code begins here:  *** wnt
	------ ---------------------------------------------
	----PRINT CONVERT(VARCHAR(MAX),GETDATE())
	----Set @dwBomName = @execution_id  -- --'32-901-08-01'  '32-910-01-06-proto'
		select top 1 @execution_id = execution_id from @execution_process

	-- Execute Code in this block: ----------------------- ~~
	-- Execute Code in this block: -----------------------
	-- Execute Code in this block: -----------------------
	print 'Execution_id: ' + convert(varchar(max),@execution_id)
	Set @dwBomName = @execution_id  -- --'32-901-08-01'  '32-910-01-06-proto'
-- ----------------------------------------------------------------
	Set @dwIdx = @counter 
	
	truncate table #parents
	truncate table #children
	truncate table #passX	
	truncate table #results
--  select * from #parents
--	select * from #children
--  select * from #children where part_id = '6AL4V-187 2.21 x 4.48'

	-- === Section 1 =======================================
--
-- *** Get materials Begins ***
-- =====================================================


--  children pass 1 ------------------------------------------
--  Note: sub_id is the data point for legs in the bom
--
-- ---------------------------------------------------
-- ~~!
-- Children_Pass1

insert into #children (
	[type]
	,base_id
	,lot_id
	,split_id
	,sub_id
	,operation_seq_no
	,piece_no
	,subord_wo_sub_id
	,part_id
	,status
	,qty_per
	,calc_qty
	,[level] 

	,usage_um 
	)

select 
	    [type] = convert(nchar(1),x.workorder_type ) 						-- nchar(1) 
       ,base_id = convert(nvarchar(30),x.workorder_base_id)   			-- nvarchar(30) 
       ,lot_id = convert(nvarchar(3), x.workorder_lot_id) 				-- nvarchar(3)
       ,split_id = convert(nvarchar(3), x.workorder_split_id)			-- nvarchar(3)
       ,sub_id = convert(nvarchar(3),x.workorder_sub_id)					-- nvarchar(3)
       ,operation_seq_no = convert(smallint,x.operation_seq_no) -- smallint
       ,piece_no = convert(smallint,x.piece_no)						-- smallint 
       ,subord_wo_sub_id = convert(nvarchar(3),x.subord_wo_sub_id) 	-- nvarchar(3)
       ,part_id = convert(nvarchar(30),x.part_id )     				-- nvarchar(30)

	   	, [status] = convert( nchar(1),x.status)
		, qty_per = convert( decimal(15,8),x.qty_per)
        , calc_qty = convert( decimal(14,4),x.calc_qty)

		,level = iif(coalesce(subord_wo_sub_id,x.workorder_sub_id,0) > 0, 1,0)

		,usage_um = CONVERT( nvarChar(15), usage_um)

    -- -- into #children
	-- select *
   from requirement x (nolock) -- _Children_Pass1
   JOIN PART_SITE ps
   --on x.WORKORDER_BASE_ID = ps.PART_ID
   on x.part_id = ps.PART_ID
   and x.WORKORDER_LOT_ID = isnull(ps.engineering_mstr,0)
   and ps.SITE_ID = 'sk01'

    where (1=1) 
	-- some parts are both parent and child. 
    ---and isnull(x.part_id,'') <> isnull(x.workorder_base_id,'') 
	and x.workorder_type = 'm'
    and subord_wo_sub_id is null
	--order by part_id

profile_data_for_requirement:
-- -- CHILD select * from #temp2 where base_id = '453T1450-9073'
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- ~~  CHILD

--select * from requirement where SUBORD_WO_SUB_ID is null and workorder_type='M'
--select * from requirement where SUBORD_WO_SUB_ID is null and workorder_type = 'M' and workorder_sub_id > 0
-- select * from requirement where part_id = '453T1450-15' and workorder_type = 'M'



--  parents pass 1 ------------------------------------------
--
-- -- _Parents_Pass1
-- ---------------------------------------------------

insert into #parents
(
	[type]
	,base_id
	,lot_id
	,split_id
	,sub_id
	,operation_seq_no
	,piece_no
	,subord_wo_sub_id
	,part_id
	,status
	,qty_per
	,calc_qty
	,[level]

	,usage_um
)


select --distinct
	[type] = convert(nchar(1),wo.type) 						-- nchar(1) 
    ,base_id = convert(nvarchar(30),null)   			-- nvarchar(30) 
   -- ,base_id = convert(nvarchar(30),wo.BASE_ID)   			-- nvarchar(30) 
    ,lot_id = convert(nvarchar(3), wo.lot_id) 				-- nvarchar(3)
    ,split_id = convert(nvarchar(3), wo.split_id)			-- nvarchar(3)
    ,sub_id = convert(nvarchar(3),wo.sub_id)					-- nvarchar(3)

    ,operation_seq_no = convert(smallint,null) -- smallint
    ,piece_no = convert(smallint,null)						-- smallint 
    ,subord_wo_sub_id = convert(nvarchar(3),null) 	-- nvarchar(3)
    ,part_id = convert(nvarchar(30),wo.part_id )     				-- nvarchar(30)

	, [status] = convert( nchar(1),wo.status)
    , qty_per = convert( decimal(15,8),1)
    , calc_qty = convert( decimal(14,4),1)
	, convert(int,0) as level

	, usage_um = convert(nvarchar(15),null)
from   work_order wo  --  _Parents_Pass1
   join part_site ps
   on wo.PART_ID = ps.PART_ID
   and wo.LOT_ID = ps.ENGINEERING_MSTR
   and ps.SITE_ID = 'sk01'
where (1=1) 
and wo.type = 'm'
--  testing 3/5
and wo.BASE_ID = @dwBomName
and wo.sub_id = '0'
order by part_id
;

set @RowCountParents1 = @@ROWCOUNT
print 'Row count parents pass 1: ' + convert(varchar(max), @RowCountParents1) + '. . .' + CONVERT(VARCHAR(MAX), @dwBomName)
-- -- PARENT
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS 1ST PASS
-- ~~  PARENT

--  BOM ------------------------------------------
--  Iterative CTE
--  Pass 1
-- ---------------------------------------------------
-- ~~

;with bom (dwIdx, dwBomName ,base_id, part_id, lot_id, piece_no,partPath, [level], sortX, tab, SUBORD_WO_SUB_ID, sub_id,split_id
    ,up_level_part_id, operation_seq_no, [status], qty_per, calc_qty, usage_um  )
as
(
-- anchor member definition: parent.part_id = children.base_id
    select 
		 @dwIdx dwIdx
		,@dwBomName dwBomName

	    ,e.base_id
		, e.part_id
		, e.lot_id, e.piece_no
	
		,cast(
		cast(row_number() over(partition by e.base_id order by e.lot_id,e.operation_seq_no,e.piece_no) as varchar(max)) 
		as varchar(30)
		)
		as [partPath]
		
		,0 as level
		,row_number()over(partition by e.base_id order by e.lot_id,e.operation_seq_no,e.piece_no) / power(10.0,1) as sortx

		,4 as tab
		,	e.SUBORD_WO_SUB_ID
		,   e.sub_id
		,   e.split_id

		,   e.part_id up_level_part_id
		,   e.operation_seq_no

		, e.[status] 
		, e.qty_per 
		, e.calc_qty 

		,usage_um
    -- select *  
    from #parents as e
    UNION ALL
-- recursive member definition 
    select 
		 @dwIdx dwIdx
		,@dwBomName dwBomName
		
		,e.base_id, e.part_id, e.lot_id, e.piece_no 

	    ,cast(
		d.[partpath] +'-'+ cast(row_number()over(partition by e.base_id order by d.[level] + 1,e.lot_id,e.operation_seq_no,e.piece_no) as varchar(max))
        as varchar(30)
		) as partPath

	    ,d.[level] + 1
		,d.sortx + row_number()over(partition by e.base_id order by d.[level] + 1,e.lot_id,e.operation_seq_no,e.piece_no) / power(10.0,d.[level]+1)
		
		,4 as tab
		,e.SUBORD_WO_SUB_ID
		,e.sub_id
		,e.split_id


		,d.part_id up_level_part_id
		,e.operation_seq_no

		, e.[status] 
		, e.qty_per 
		, e.calc_qty 

		, e.usage_um
	-- select * from #children where base_id = '453T1450-9013' 
    from #children as e
    inner join bom as d
     on e.base_id = d.part_id
   -- Update 6/4/2020 parent must have eng mstr
	join part_site ps
	on d.part_id = ps.part_id
	and ps.site_id = 'SK01'
	and ps.engineering_mstr is not null
	 -- update 2020-03-06.1, 2020-03-12.1
 	 -- legs components are assumed at level 1, links should be up-level not down-level
	 -- this prevents parts like 453T1450-15, a multilevel part, from down-level (e.g. 20243C-063 CMP)  
	 --and e.level >= d.level
	 -- This version forces uplevel part to fix parts like 151W1583-3
	 --and ISNULL(e.operation_seq_no,'01') <> isnull(d.operation_seq_no,'00')
     and e.sub_id = d.sub_id
	 and e.lot_id = d.lot_id
	 and e.split_id = d.split_id


)

-- select * from #passX
-- select * from #parents
-- select * from #children where base_id = '453T1450-9013' and part_id = '453T1450-15' 
-- select * from #children where base_id = '453T1450-9013' and part_id = '20243C-063 CMP' 
-- select * from #children where base_id = '453T1450-15'

-- select * from requirement where (1=1) and workorder_type = 'm' and workorder_base_id = '284T4224-1 -- '146T5500-114'

-- statement that executes the cte
	insert into #passX
	(
	 dwIdx	
	,dwBomName	--
	,dwBomId	
	,base_id	
	,part_id	
	,[description]	
	,lot_id	
	,piece_no	
	,level	
	,tab	
	,partPath	
	,sortX
	,Depth	
	,SUBORD_WO_SUB_ID	
	,sub_id	
	,split_id	
	,up_level_part_id	
	,comment	
	,operation_seq_no	
	,status	
	,qty_per	
	,calc_qty	

	,usage_um
	,level2
	)

	select 
		 dwIdx
		,dwBomName
		,dwBomId = 'BOM-' + CONVERT(NVARCHAR(30),dwBomName)
		,base_id, part_id
		,left(convert(varchar(30), p.id) + ' ' + isnull(p.[description],''),27) [description]
		, lot_id
		, piece_no
		, [level]
		, tab
		, cast( 
		 partPath
		 as varchar(30)
		 ) as partPath
		, sortX = Case level when 0 then sortx + 1 else sortX + 20 end-- pass 1
		, Depth = (tab * [level])
		,SUBORD_WO_SUB_ID
		,sub_id
	
		,split_id
		,up_level_part_id
		,comment = CAST(iif(SUBORD_WO_SUB_ID is not null, 'Leg', NULL) AS VARCHAR(20))
		,operation_seq_no

		, b.[status] 
		, b.qty_per 
		, b.calc_qty 

		,b.usage_um
		,level2 = 1
	from bom b
	join part p
	on b.part_id = p.id

	where (1=1)
	and level >= 0
	order by sortx asc;

	-- select * from #passX



-- insert 2  pass 1------------------------------
--
--
-- ---------------------------------------
    insert into #bom(
		 dwIdx
		,dwBomName
		,dwBomId
		,base_id
		,part_id
		,description
		,lot_id
		,piece_no
		,level
		,tab
		,partPath
		,sortX
		,Depth
		,SUBORD_WO_SUB_ID
		,sub_id
		,split_id
		,up_level_part_id
		,comment
		,operation_seq_no
		,status
		,qty_per
		,calc_qty

		,usage_um
		,level2
	)

	select  
		 dwIdx
		,dwBomName
		,dwBomId
		,base_id
		,part_id
		,description
		,lot_id
		,piece_no
		,level
		,tab
		,partPath
		,sortX
		,Depth
		,SUBORD_WO_SUB_ID
		,sub_id
		,split_id
		,up_level_part_id
		,comment
		,operation_seq_no
		,status
		,qty_per = iif(level=0,null,qty_per)
		,calc_qty

		,usage_um
		,level2  -- first pass non leg fact
	FROM #passX p1
	where (1=1)
	and p1.sub_id = 0
	order by dwBomName, sortx 

-- select * FROM #passX

	-- Execution of Code Ends /////////////////////////// wnt
	-- --------------------------------------------------
	if @counter % 100 = 0
		print convert(varchar(max), @counter) + ': ' + CONVERT(VARCHAR(MAX),@execution_id) + ' - '

    END TRY

    BEGIN CATCH
                            
    END CATCH

	SET @counter = @counter + 1
	IF @counter > @MaxCount
	  BREAK;

	


-- FETCH NEXT FROM execution_cursor INTO @execution_id
--END  -- WHILE
--CLOSE execution_cursor
-- ----- LOOP 1 ENDS /////////////////////////////////////// ~~
DELETE 
FROM @execution_process
where execution_id = @execution_id
PRINT CONVERT(VARCHAR(MAX),GETDATE())
--This deletes the 1 row that we have just selected\
END -- WHILE
-- ----- PASS 1 ENDS /////////////////////////////////////// ~~

--DEALLOCATE execution_cursor
END  -- section

-- ~~ pass 1 /////////////////////////////////////////

------ create schema WilliamT
--truncate table [WilliamT].[BOM_Indented]


-- Pass in test
--select * from #bom order by dwBomName, sortx 

PRINT 'Time Pass 1: ' +  CONVERT(VARCHAR(MAX),getdate())
-- select *255U0183-3 from #bom
-- select * from WilliamT.BOM_Indented order by dwBomName, sortx 
profile_qty_dependent1:

-- select * from WilliamT.BOM_Indented WHERE part_id = '287T1034-983'

parts_list1:

save_temp_audits:

select
*
into #temp1
from #parents

select
*
into #temp2
from #children

-- select * from #temp1
-- select * from #temp2 where base_id = '151W1583-3' and operation_seq_no > '0'



-- ~~ Pass 2
-- ****** PART 2 2ND PASS  ***********************************************
-- ****** PART 2 2ND PASS  ***********************************************
-- ****** PART 2 2ND PASS  ***********************************************
-- ****** PART 2 2ND PASS  ***********************************************
-- ****** PART 2 2ND PASS  ***********************************************
-- ****** PART 2 2ND PASS  ***********************************************


-- Cursor Pass 2--------------------------------------
-- init cursor control variables
--
-- ---------------------------------------------
-- PASS 2 -------------------------------------~~
SET @counter = 0
set @execution_id = null;
delete from @execution_process
insert into @execution_process
select * from @execution_process2

-- declare iterator and loop
BEGIN -- section

---- ~~ Pass 2
------Truncate table #bom
--OPEN execution_cursor
--FETCH NEXT FROM execution_cursor INTO @execution_id
            
--WHILE @@FETCH_STATUS = 0
--BEGIN
WHILE EXISTS	(SELECT execution_id  FROM @execution_process)
--This is a basic WHILE loop that runs as long as there is data in the variable table
 
BEGIN

	select top 1 @execution_id = execution_id from @execution_process
                        
    BEGIN TRY


	-- Execute Code in this block: -----------------------
	-- Execute Code in this block: -----------------------
	-- Execute Code in this block: -----------------------
	print 'Declarations Pass 2: ' + convert(varchar(max),@execution_id) 
        + ' . . . ' + convert(varchar(max),@dwBomName)

	Set @dwBomName = @execution_id  -- --'32-901-08-01'  '32-910-01-06-proto'
-- ----------------------------------------------------------------

	Set @dwIdx = @counter 
	
	truncate table #parents
	truncate table #children
	truncate table #passX	
	truncate table #results

-- === Section 1  =======================================

-- =====================================================
--  children Pass 2 ------------------------------------------
--
-- ---------------------------------------------------
-- ~~!

-- _Children_Pass2

insert into #children (
	[type]
	,base_id
	,lot_id
	,split_id
	,sub_id
	,operation_seq_no
	,piece_no
	,subord_wo_sub_id
	,part_id
	,status
	,qty_per
	,calc_qty
	,[level] 
	
	,usage_um
	)

select 
	    [type] = convert(nchar(1),x.workorder_type ) 						-- nchar(1) 
       ,base_id = convert(nvarchar(30),x.workorder_base_id)   			-- nvarchar(30) 
       ,lot_id = convert(nvarchar(3), x.workorder_lot_id) 				-- nvarchar(3)
       ,split_id = convert(nvarchar(3), x.workorder_split_id)			-- nvarchar(3)
       ,sub_id = convert(nvarchar(3),x.workorder_sub_id)					-- nvarchar(3)
       ,operation_seq_no = convert(smallint,x.operation_seq_no) -- smallint
       ,piece_no = convert(smallint,x.piece_no)						-- smallint 
       ,subord_wo_sub_id = convert(nvarchar(3),x.subord_wo_sub_id) 	-- nvarchar(3)
       ,part_id = convert(nvarchar(30),x.part_id )     				-- nvarchar(30)

	   	, [status] = convert( nchar(1),x.status)
		, qty_per = convert( decimal(15,8),x.qty_per)
        , calc_qty = convert( decimal(14,4),x.calc_qty)

		,level = iif(coalesce(subord_wo_sub_id,x.workorder_sub_id,0) > 0, 1,0)

		,usage_um = convert(nvarchar(15),x.usage_um)
	-- --into #children

	-- select x.workorder_lot_id, isnull( p.ENGINEERING_MSTR,0) ENGINEERING_MSTR
    from requirement x (nolock)   -- _Children_Pass2
	-- UPDATE 2020-05-14 lot in requirement table must be constrained
	join part_site p (nolock)
	on x.PART_ID = p.PART_ID
	and p.SITE_ID = 'sk01'

	AND x.WORKORDER_LOT_ID = isnull( p.ENGINEERING_MSTR,0)
	-- //
    where (1=1) 
	and x.workorder_type = 'm'

	AND x.WORKORDER_SPLIT_ID = '0' 
	-- update 2020-05-13 The child set for legs has subord null
	and x.SUBORD_WO_SUB_ID is null
	-- See Proof #2 Testing 5/18
	AND convert(int,x.WORKORDER_SUB_ID) > 0 
	
	order by part_id

	--CREATE CLUSTERED INDEX Cidx_Child ON #children (base_id, lot_id, split_id, sub_id, part_id)

	profile_child_set_pass2:
	
-- ~~ CHILD  /////////////////////////
-- 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS
-- 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS
-- ~~ CHILED

	-- select * FROM #children where part_id = '255U0186-1' -- '255U0183-3'
	-- select * FROM #parents where base_id = '255U0183-3'
	---- select * FROM requirement where part_id = '255U0186-1' and workorder_base_id = '255U0183-3'

	--select  
	--  r.WORKORDER_TYPE, r.WORKORDER_BASE_ID, WORKORDER_SUB_ID, OPERATION_SEQ_NO, PIECE_NO
	--  ,SUBORD_WO_SUB_ID, PART_ID

	--from requirement r where (1=1) and workorder_type = 'M' and WORKORDER_BASE_ID = '287T1034-983'
	--and WORKORDER_SUB_ID > 0

	-- PASS 3??<   SELECT distinct part_id, WORKORDER_TYPE FROM requirement where WORKORDER_sub_id > 0 AND subord_wo_SUB_ID IS NOT NULL
	
	-- PASS 3??<   SELECT distinct part_id, WORKORDER_TYPE,* FROM requirement where WORKORDER_sub_id > 0 AND subord_wo_SUB_ID IS NOT NULL
	
	-- use case 2:58
	-- use case 2:58.1 subord_wo_sub_id is null
	-- PASS 3??<   SELECT distinct WORKORDER_BASE_ID, part_id, WORKORDER_TYPE,* FROM requirement where WORKORDER_sub_id > 0 AND workorder_type = 'M' and subord_wo_sub_id is null
	-- use case 2:58.2 if leg, and subord_wo_sub_id is not null then = empty set
	-- PASS 3??<  <QUERY RENDERS EMPTY SET>
	-- use case 3:09 sub id 0, subord_wo_SUB_ID IS NULL
	-- PASS 3??<   SELECT distinct WORKORDER_BASE_ID, part_id, WORKORDER_TYPE,* FROM requirement where WORKORDER_sub_id = 0 AND workorder_type = 'M' and subord_wo_sub_id is null
	-- use case 3:09 sub id 0, subord_wo_SUB_ID IS NOT NULL
	-- PASS 3??<   SELECT distinctWORKORDER_BASE_ID,  part_id, WORKORDER_TYPE,* FROM requirement where WORKORDER_sub_id = 0 AND workorder_type = 'M' and subord_wo_sub_id is NOT null
	-- use case 3:27 
	 --SELECT distinct WORKORDER_BASE_ID,  part_id, WORKORDER_TYPE,*
	 --FROM requirement where WORKORDER_sub_id > 0 AND workorder_type = 'M' 
	 --and subord_wo_sub_id is null
	 --and part_id = '20243C-063 CMP'

	 ---- 453T1450-9007
	 --SELECT distinct WORKORDER_BASE_ID,  part_id, WORKORDER_TYPE,*
	 --FROM requirement where WORKORDER_sub_id > 0 AND workorder_type = 'M' 
	 --and subord_wo_sub_id is null
	 --and workorder_base_id = '453T1450-9007'

	 --	 -- 453T1450-9007
	 --SELECT distinct WORKORDER_BASE_ID,  part_id, WORKORDER_TYPE,*
	 --FROM requirement where WORKORDER_sub_id > 0 AND workorder_type = 'M' 
	 --and subord_wo_sub_id is null
	 --and workorder_base_id = '453T1450-9007'
	 --and part_id = '20243C-063 CMP'

	 --select * from WORK_ORDER
	 --where type = 'M'
	 --and SUB_ID > 0

---- ~~ ----------------------------------------------------------
---------------------------------------------------------------


--  parents Pass 2 ------------------------------------------
-- ~~
-- _Parents_Pass2
-- ---------------------------------------------------

insert into #parents
(
	[type]
	,base_id
	,lot_id
	,split_id
	,sub_id
	,operation_seq_no
	,piece_no
	,subord_wo_sub_id
	,part_id
	,status
	,qty_per
	,calc_qty
	,[level]

	,usage_um
)


select --distinct
	[type] = convert(nchar(1),x.workorder_type) 						-- nchar(1) 
    ,base_id = convert(nvarchar(30),workorder_base_id)   			-- nvarchar(30) 
    ,lot_id = convert(nvarchar(3), x.workorder_lot_id) 				-- nvarchar(3)
    ,split_id = convert(nvarchar(3), x.workorder_split_id)			-- nvarchar(3)
    ,sub_id = convert(nvarchar(3),x.workorder_sub_id)					-- nvarchar(3)

    ,operation_seq_no = convert(smallint,x.operation_seq_no) -- smallint
    ,piece_no = convert(smallint,x.piece_no)						-- smallint 
    ,subord_wo_sub_id = convert(nvarchar(3),x.subord_wo_sub_id) 	-- nvarchar(3)
    ,part_id = convert(nvarchar(30),x.part_id )     				-- nvarchar(30)

	, [status] = convert( nchar(1),x.status)
    , qty_per = convert( decimal(15,8),1)
    , calc_qty = convert( decimal(14,4),1)
	, convert(int,1) as level

	, usage_um = convert(nvarchar(15),usage_um)

---from   work_order wo 
--where (1=1) 
--and wo.type = 'm'
----  testing 3/5
--and wo.BASE_ID = @dwBomName
--and wo.sub_id = '0'

-- ~~ PARENTS

from requirement x --  _Parents_Pass2
JOIN PART_SITE ps
on x.WORKORDER_BASE_ID = ps.PART_ID
and ps.SITE_ID = 'sk01'
and x.WORKORDER_LOT_ID = ps.ENGINEERING_MSTR

where (1=1) 
and x.workorder_type = 'm' 
and x.workorder_base_id = @dwBomName
-- note that the child set will/should render workorder_sub_id > 0
and x.workorder_sub_id = 0
and x.SUBORD_WO_SUB_ID is not null

order by part_id;

Set @RowCountParents2 = @@ROWCOUNT

print 'Row Count Parents Pass 2: ' + convert(varchar(max),@RowCountParents2) + ' . . . ' + convert(varchar(max),@dwBomName)
-- ~~ PARENT
-- SELECT * FROM #parents
-- 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS
-- 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS 3RD PASS
-- ~~


-- select * from #children
-- select * from #parents
-- select * from #children where base_id = '453T1450-19'
-- select workorder_base_id,part_id,* from requirement x where workorder_base_id like '113W5202-1'
-- select * from #children where part_id = '20243C-063 CMP' and sub_id = 1
-- ~~
--Pass 1 - Regular routing for components of non-legs  (child.base = parent.part)
--Pass 2 - The bom is the parent for legs (child.sub_id = parent.subord_wo_sub_id)
--Pass 3 - Regular routing for components of legs (child.base = parent.part)

--select  
--  r.WORKORDER_TYPE, r.WORKORDER_BASE_ID, WORKORDER_SUB_ID  --, OPERATION_SEQ_NO, PIECE_NO
--  ,SUBORD_WO_SUB_ID, PART_ID
--from requirement r where (1=1) and workorder_type = 'M' and SUBORD_WO_SUB_ID is not null
--and WORKORDER_BASE_ID = @dwBomName -- '255U0183-3' --'453T1450-9017'

--select  
--  r.WORKORDER_TYPE, r.WORKORDER_BASE_ID, WORKORDER_SUB_ID  --, OPERATION_SEQ_NO, PIECE_NO
--  ,SUBORD_WO_SUB_ID, PART_ID
--from requirement r 
--where (1=1) and workorder_type = 'M' 
--and SUBORD_WO_SUB_ID is not null
----and WORKORDER_BASE_ID = @dwBomName  -- '255U0183-3' --'453T1450-19'
--   and part_id in (
--		 '255U0186-1'
--		,'255U0188-3'
--		,'255U0190-3'
--   )



-- select * from #children where base_id = '287T1034-983'

--  BOM ------------------------------------------
--  Iterate thru routing
--  Pass 2
-- ---------------------------------------------------
-- ~~

;with bom (dwIdx, dwBomName ,base_id, part_id, lot_id, piece_no,partPath, [level], sortX, tab, SUBORD_WO_SUB_ID, sub_id,split_id
    ,up_level_part_id, operation_seq_no, [status], qty_per, calc_qty, usage_um  )
as
(
-- anchor member definition: parent.part_id = children.base_id
    select 
		 @dwIdx dwIdx
		,@dwBomName dwBomName

	    ,e.base_id
		, e.part_id
		, e.lot_id, e.piece_no
	
		,cast(
		cast(row_number() over(partition by e.base_id order by e.lot_id,e.operation_seq_no,e.piece_no) as varchar(max)) 
		as varchar(30)
		)
		as [partPath]
		
		,1 as level
		,row_number()over(partition by e.base_id order by e.lot_id,e.operation_seq_no,e.piece_no) / power(10.0,1) as sortx

		,4 as tab
		,	e.SUBORD_WO_SUB_ID
		,   e.sub_id
		,   e.split_id

		,   e.part_id up_level_part_id
		,   e.operation_seq_no

		, e.[status] 
		, e.qty_per 
		, e.calc_qty
		
		, e.usage_um 

    -- select *  
    from #parents as e
    UNION ALL
-- recursive member definition 
    select 
		 @dwIdx dwIdx
		,@dwBomName dwBomName
		
		,e.base_id, e.part_id, e.lot_id, e.piece_no 

	    ,cast(
		d.[partpath] +'-'+ cast(row_number()over(partition by e.base_id order by d.[level] + 1,e.lot_id,e.operation_seq_no,e.piece_no) as varchar(max))
        as varchar(30)
		) as partPath

	    ,d.[level] + 1
		,d.sortx + row_number()over(partition by e.base_id order by d.[level] + 1,e.lot_id,e.operation_seq_no,e.piece_no) / power(10.0,d.[level]+1)
		
		,4 as tab
		,e.SUBORD_WO_SUB_ID
		,d.sub_id
		,e.split_id


		,d.part_id up_level_part_id
		,e.operation_seq_no

		, e.[status] 
		, e.qty_per 
		, e.calc_qty 

		, e.usage_um

	-- select * from #children where base_id = '453T1450-19' 
    from #children as e
    inner join bom as d
	 -- update 2020-03-06.1, 2020-03-12.1
	 -- update 2020-05-03.1, 2020-05-14.1

	 -- Version 3 ** update 2020-05-14.1
	 -- PASS 3 IS LEG ROUUTING #2 CHILD.sub_id = PARENT.subord_wo_sub_id
	         -- note that the c.base -- > p.part route is removed for pass 3
		--There are two routings for components of legs and these data-sets are created by an iterative query.
		--1)	Is via the normal routing, with the following constraints
		--a.	 the parent.part_id  = the child.base_id
		--b.	The parent.[Lot/engineering master] = child.[ Lot/engineering master] *
		--c.	The parent.sub_id = child.sub_id (the sub is implicitly always 0 in a BOM)
		-- *** pass 3 ###
		--2)	Is via the legs routing for components, with the following constraint
		--a.	The parent.subord_wo_subid = child.sub_id
		--b.	The parent.[Lot/engineering master] = child.[ Lot/engineering master] *
		--c.	The parent.part_id = @dwBomName
		--•	Lot is already constrained by the join to work order

	 -- Version 2 *** update 2020-05-13.1
	 -- The same iteration, but different route (different join in iterative cte)
	 -- The join is from a leg to a child.
	 -- Version 1 SUPERCEDED BY update 2020-05-03.1 
	 -- Test BOM and component 20243C-063 CMP, a child of 453T1450-19 (leg) which is _
	 -- a child-leg of 453T1450-9017
 	 -- legs components are assumed at level 1, links should be up-level not down-level
	 -- this prevents parts like 453T1450-15, a multilevel part, from down-level (e.g. 20243C-063 CMP)  
	 -- The key is to find a part that is both parent and child leg AND has a child. e.g. 20243C-063 CMP)

	 on
	 -- update 2020- the leg's child set is joined from a leg parent to non-leg child 
	  e.sub_id = d.subord_wo_sub_id
	 and e.base_id = @dwBomName -- d.part_id
	  
	 and e.lot_id = d.lot_id
	 and e.split_id = d.split_id


)

-- select * from #passX
-- select * from #parents
-- select * from #children where base_id = '453T1450-9013' and part_id = '453T1450-15' 
-- select * from #children where base_id = '453T1450-9013' and part_id = '20243C-063 CMP' 
-- select * from #children where base_id = 

-- select * from requirement where (1=1) and workorder_type = 'm' and workorder_base_id = '453T1450-9013'


-- statement that executes the cte
	insert into #passX
	(
	 dwIdx	
	,dwBomName	--
	,dwBomId	
	,base_id	
	,part_id	
	,[description]	
	,lot_id	
	,piece_no	
	,level	
	,tab	
	,partPath	-- prepend '1-' if level2 = 2
	,sortX	
	,Depth	
	,SUBORD_WO_SUB_ID	
	,sub_id	
	,split_id	
	,up_level_part_id	
	,comment	
	,operation_seq_no	
	,status	
	,qty_per	
	,calc_qty	

	,usage_um
	,level2
	)

	select 
		 dwIdx
		,dwBomName
		,dwBomId = 'BOM-' + CONVERT(NVARCHAR(30),dwBomName)
		,base_id, part_id
		,left(convert(varchar(30), p.id) + ' ' + isnull(p.[description],''),27) [description]
		, lot_id
		, piece_no
		, [level]
		, tab
		, cast( 
		 '1-' + partPath
		 as varchar(30)
		 ) as partPath
		, sortX + 10
		, Depth = (tab * [level])
		,SUBORD_WO_SUB_ID
		,sub_id
	
		,split_id
		,up_level_part_id
		,comment = CAST(iif(SUBORD_WO_SUB_ID is not null, 'Leg', NULL) AS VARCHAR(20))
		,operation_seq_no

		, b.[status] 
		, b.qty_per 
		, b.calc_qty 

		, b.usage_um
		, level2 = 2  -- fact 2 with legs
	from bom b
	join part p
	on b.part_id = p.id

	where (1=1)
	order by sortx asc;

	-- select * from #passX
	-- insert 2 ------------------------------
	--
	--
	-- ---------------------------------------
    insert into #bom(
		 dwIdx
		,dwBomName
		,dwBomId
		,base_id
		,part_id
		,description
		,lot_id
		,piece_no
		,level
		,tab
		,partPath
		,sortX
		,Depth
		,SUBORD_WO_SUB_ID
		,sub_id
		,split_id
		,up_level_part_id
		,comment
		,operation_seq_no
		,status
		,qty_per
		,calc_qty

		,usage_um
		,level2
	)

	select  
		 dwIdx
		,dwBomName
		,dwBomId
		,base_id
		,part_id
		,description
		,lot_id
		,piece_no
		,level
		,tab
		,partPath
		,sortX
		,Depth
		,SUBORD_WO_SUB_ID
		,sub_id
		,split_id
		,up_level_part_id
		,comment
		,operation_seq_no
		,status
		,qty_per = iif(level = 0, null, qty_per)
		,calc_qty

		,usage_um
		,level2  -- fact relational integrity has leg(s)
	FROM #passX p1
	where (1=1)
	order by dwBomName, level2, sortx 

	-- Execution of Code Ends /////////////////////////// wnt
	-- --------------------------------------------------
	if @counter % 100 = 0
		print convert(varchar(max), @counter) + ': ' + CONVERT(VARCHAR(MAX),@execution_id) + ' - '

    END TRY

    BEGIN CATCH
                            
    END CATCH

	print 'count of pass 2: ' + convert(varchar, @counter)

	SET @counter = @counter + 1
	IF @counter > @MaxCount
	  BREAK;

	
-- ----- LOOP ENDS /////////////////////////////////////// ~~~
DELETE 
FROM @execution_process
where execution_id = @execution_id
---- FETCH NEXT FROM execution_cursor INTO @execution_id
END  -- WHILE
----CLOSE execution_cursor

--This deletes the 1 row that we have just selected\

----DEALLOCATE execution_cursor
END  -- section
-- ----- PASS 2 ENDS ///////////////////////////////////// ~~~


---- create schema WilliamT
--truncate table [WilliamT].[BOM_Indented]

--insert into
--[WilliamT].[BOM_Indented]

select 
    * 
from #bom
--where up_level_part_id = '255U0186-1' -- 255U0186-1 -- 255U0190-3 -- 255U0188-3
order by dwBomName, level2, sortx 

PRINT 'Time: ' +  CONVERT(VARCHAR(MAX),getdate())
-- select * from #bom
-- select * from WilliamT.BOM_Indented order by dwBomName, sortx 
profile_qty_dependent1_2:

-- select * from WilliamT.BOM_Indented WHERE part_id = '287T1034-983'

parts_list1_2:
-- ///////////////////////////////////////////////////////////////
GO


---