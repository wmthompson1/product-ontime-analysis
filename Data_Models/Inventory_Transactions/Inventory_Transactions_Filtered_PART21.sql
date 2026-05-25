
/**********************************************************************************************
Code Base 3.2
Description:  Need to render standars and detail at Ops Level 

Code Base: 3.2.4 Inventory - On Hand Reconciled    

Date        Modified By         Change Description
----------  ------------------  ------------------------------------------------------------
04/09/2026    William Thompson    Created.
04/14/2026    William Thompson    Updated work order filter criteria and grouping for transaction-level columns
   


The changes:

trace_id — concatenated via STRING_AGG(CAST(ti.trace_id AS NVARCHAR(MAX)), ', ')
trace_lot — concatenated via STRING_AGG(tr.APROPERTY_1, ', ')
trace_unavailable_qty, trace_in_qty, trace_out_qty — summed with SUM()
GROUP BY added with all transaction-level columns so each row represents one part_id + transaction_id
, and effect_on_qty_on_hand reflects the single transaction's impact without duplication from multiple trace records.


** PART I OF 2 **

-- Link to: Documentation\Schema\Data_Models\Inventory_Transactions\Inventory_Transaction_Terminology_Guide.md
Inventory Transaction Terminology Guide
UI Action	CLASS	TYPE	QOH Effect
Receipt	R	I	↑
Issue to WO	I	O	↓
Adjust In	A	I	↑
Adjust Out	A	O	↓
Issue Return	I	I	↑
Receipt Return	R	O	↓

Requirement Table 
**********************************************************************************************/


SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results
IF OBJECT_ID('tempdb..#trace_inv_trans') IS NOT NULL DROP TABLE #trace_inv_trans
IF OBJECT_ID('tempdb..#trace_profile') IS NOT NULL DROP TABLE #trace_profile
IF OBJECT_ID('tempdb..#Trace') IS NOT NULL DROP TABLE #Trace
IF OBJECT_ID('tempdb..#part_trace_maint') IS NOT NULL DROP TABLE #part_trace_maint

IF OBJECT_ID('tempdb..#inventory_trans') IS NOT NULL DROP TABLE #inventory_trans
IF OBJECT_ID('tempdb..#ixact_agg_by_part') IS NOT NULL DROP TABLE #ixact_agg_by_part

IF OBJECT_ID('tempdb..#planning_on_hand') IS NOT NULL DROP TABLE #planning_on_hand
IF OBJECT_ID('tempdb..#tixact_agg_by_xact_id') IS NOT NULL DROP TABLE #tixact_agg_by_xact_id
IF OBJECT_ID('tempdb..#tixact_agg_by_part_id') IS NOT NULL DROP TABLE #tixact_agg_by_part_id
IF OBJECT_ID('tempdb..#results_agg') IS NOT NULL DROP TABLE #results_agg

IF OBJECT_ID('Datawarehouse.managedData.Inventory_On_Hand_Reconcilable') IS NOT NULL DROP TABLE Datawarehouse.managedData.Inventory_On_Hand_Reconcilable
-- #Inventory_On_Hand_Reconcilable
IF OBJECT_ID('tempdb..#Inventory_On_Hand_Reconcilable') IS NOT NULL DROP TABLE #Inventory_On_Hand_Reconcilable

IF OBJECT_ID('tempdb..#temp1') IS NOT NULL DROP TABLE #temp1
IF OBJECT_ID('tempdb..#temp2') IS NOT NULL DROP TABLE #temp2
IF OBJECT_ID('tempdb..#temp3') IS NOT NULL DROP TABLE #temp3
IF OBJECT_ID('tempdb..#temp4') IS NOT NULL DROP TABLE #temp4
IF OBJECT_ID('tempdb..#temp5') IS NOT NULL DROP TABLE #temp5


DECLARE @Tester int
  -- ,@Part_ID nvarchar(30) =  null; -- '71507E-1100153'
declare @part_id nvarchar(250) = 'BACN10YK3D012N16U'; --'417A4182-2'  --  '417A4182-2' ; --'BACN11G3A7CD';  -- '70750B-071-MIL-NG';
--'25243C-112 X 11.25 X 68.00' --'65B83903-7' -- '315A6015-14'  -- '287T4518-27' -- 315A6015-14 --  'BACR10AK10C'  -- '212A1214-13'  -- 'BACR10AK10C'
-- ,@SITE_id nvarchar(30) -- = 'SK01'

Set @Tester = 0
--Set @SITE_id = 'SK01'
DECLARE  
 		    @workorder_TYPE 		nchar(1) = 'W'
           ,@workorder_BASE_ID 	nvarchar(30) = null -- '1808412'-- '1807646'
           ,@workorder_LOT_ID 	nvarchar(3) = NULL
           ,@workorder_SPLIT_ID 	nvarchar(3) = NULL
           ,@workorder_SUB_ID 	nvarchar(3) = '0'


DECLARE @Transaction_ID nvarchar(30) = null; -- '41931' ; -- '41931'  -- '138481'
--  '139140';
DECLARE @TRACE_ID nvarchar(30) = null --'135047/1';   --'183938/1'


 -- '25243C-112 X 11.25 X 68.00' --'65B83903-7' -- '315A6015-14'  -- '287T4518-27' -- 315A6015-14 --  'BACR10AK10C'  -- '212A1214-13'  -- 'BACR10AK10C'

--  inventory trans
select
  t.part_id
    , p.commodity_code
    , t.transaction_id
    , format(t.transaction_date, 'yyyy-MM-dd') as transaction_date
    , CASE
        WHEN t.TYPE = 'I' AND t.CLASS = 'R' THEN 'Receipt to Inventory'
        WHEN t.TYPE = 'O' AND t.CLASS = 'I' THEN 'Issue to Work Order'
        WHEN t.TYPE = 'O' AND t.CLASS = 'A' THEN 'Adjust Out'
        WHEN t.TYPE = 'I' AND t.CLASS = 'A' THEN 'Adjust In'
        WHEN t.TYPE = 'I' AND t.CLASS = 'I' THEN 'Issue Return'
        WHEN t.TYPE = 'O' AND t.CLASS = 'R' THEN 'Receipt Return'
        ELSE 'Unknown'
    END AS Transaction_Description
    , t.class, t.type
    , t.qty
    , (case when t.type = 'i' then t.qty else t.qty * -1 end) as effect_on_qty_on_hand
    , t.costed_qty, t.act_material_cost, t.act_labor_cost
    , t.act_burden_cost, t.act_service_cost
    , t.workorder_base_id
    , t.workorder_lot_id, t.workorder_split_id
    , t.workorder_sub_id, t.operation_seq_no, t.req_piece_no, t.cust_order_id

    , t.cust_order_line_no, t.purc_order_id
    , t.purc_order_line_no, t.warehouse_id
    , t.location_id, w.[description] warehouse_description
    --, l.description
    --, t.description
    , t.issue_reas_id, t.site_id
  
    , STRING_AGG(CAST(ti.trace_id AS NVARCHAR(MAX)), ', ') as trace_id
    , STRING_AGG(tr.APROPERTY_1, ', ') as trace_lot

    , SUM(tr.UNAVAILABLE_QTY) as trace_unavailable_qty
    , SUM(tr.IN_QTY) as trace_in_qty
    , SUM(tr.OUT_QTY) as trace_out_qty


into #inventory_trans
from inventory_trans t
join dbo.part p
  on p.id = t.part_id

  join dbo.warehouse w
  on w.id = t.warehouse_id
  join dbo.[location] l
  on w.id = l.warehouse_id
  and t.location_id = l.id
  LEFT JOIN TRACE_INV_TRANS ti WITH (NOLOCK)
  ON ti.TRANSACTION_ID = t.TRANSACTION_ID
  LEFT JOIN TRACE tr WITH (NOLOCK)
  ON tr.ID = ti.TRACE_ID

where 1=1 
-- AND t.type IN ('I', 'R')
-- and t.type = 'O'
-- and t.TRANSACTION_DATE >= '2026-01-01'
-- and p.commodity_code in ('STANDARDS','DETAILS')
-- and t.class IN ( 'i' , 'r' )
--   AND t.type IN ( 'o' , 'r' ) 
--     AND ( T.SITE_ID IN ( N'SK01' ) )
    AND (@TRANSACTION_id IS NULL OR T.TRANSACTION_ID = @TRANSACTION_id)
    and (T.PART_ID = @Part_ID   or @Part_ID IS NULL   )


-- Filter by specific transaction ID 

GROUP BY
    t.part_id, p.commodity_code, t.transaction_id, t.transaction_date
    , t.class, t.type, t.qty
    , t.costed_qty, t.act_material_cost, t.act_labor_cost
    , t.act_burden_cost, t.act_service_cost
    , t.workorder_base_id, t.workorder_lot_id, t.workorder_split_id
    , t.workorder_sub_id, t.operation_seq_no, t.req_piece_no, t.cust_order_id
    , t.cust_order_line_no, t.purc_order_id
    , t.purc_order_line_no, t.warehouse_id
    , t.location_id, w.[description]
    , t.issue_reas_id, t.site_id

ORDER BY 
t.transaction_date,
T.SITE_ID, T.PART_ID, T.TRANSACTION_ID


-- select * from #inventory_trans
create clustered index [ci_x_inv_trans_12] on #inventory_trans
(
    [transaction_id] asc
)

create nonclustered index [nci_x_inv_trans_12] on #inventory_trans
(
    [part_id] asc
) 
include([transaction_date]
,[workorder_base_id]
,[cust_order_id]
,[class]
)
select * from #inventory_trans 
where 1=1
and (workorder_base_id = @workorder_base_id or @workorder_base_id IS NULL)
ORDER BY 
transaction_date DESC,
SITE_ID, PART_ID, TRANSACTION_ID DESC