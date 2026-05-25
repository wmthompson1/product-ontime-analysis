-- S1.2.1.1 Inventory_Transactions_Filtered
-- file path: SQL_Reports/Inventory/Inventory - Transactions AI Review.sql
-- run at sql-lab-2 in prod
-- dw in stage on sql-bi-1

-- C:\SQL\Uber Query\1.2 Inventory\1.2.4 Part Trace Reconciled\part trace reconciled.1.sql
-- C:\SQL\Uber Query\1.2 Inventory\1.2.4 Part Trace Reconciled\part trace reconciled.2 xacts.sql
-- C:\SQL\Uber Query\1.2 Inventory\1.2.4 Part Trace Reconciled\part trace reconciled.2 xacts.sql
-- C:\SQL\Uber Query\1.2 Inventory\1.2.4 Part Trace Reconciled\part trace reconciled.4 xacts ETL.sql
-- C:\SQL\Uber Query\1.2 Inventory\1.2.4 Part Trace Reconciled\part trace reconciled.40 xacts ETL.sql

/**********************************************************************************************
Code Base 3.2
Description:   Reconcile trace inventory trans to inventory trans to On hand
Note:   allows maintainable code with grain to transaction id.
        There are two levels of aggregation 1 - xact id 2 - part
        Whether or not all transactions trace does not impact test,
        but rather allows a dataset to render the difference in transaction
        in case the is a variance with the amounts.    
Code Base: 3.2.4 Inventory - On Hand Reconciled    

Date        Modified By         Change Description
----------  ------------------  ------------------------------------------------------------
08/03/20    William Thompson    Created.
12/10/25    William Thompson    Updated for Code Base 3.2.4 - Determine location of parts 
12/11/25    William Thompson    Added join to work order to allow filtering by work order fields
12/11/25    William Thompson    Added trace in, out, and unavailable qty to output


TESTING:
sql agent:
  ETL Standard - Load Inventory_On_Hand_Reconcilable
ssis package - source @sql-lab-x
Visual_Load Tables Inventory On Hand Reconciled.dtsx
load Staging.dbo.Inventory_On_Hand_Reconcilable
-- select * FROM Staging.dbo.Inventory_On_Hand_Reconcilable
transform to Inventory_On_Hand_Reconcilable base table
select * from Datawarehouse.managedData.Inventory_On_Hand_Reconcilable
stored procedure
managedData.usp_Load_Inventory_On_Hand_Reconcilable
select * from Datawarehouse.managedData.Inventory_On_Hand_Reconcilable where is_reconciled = 'n'

Use Inventory Transaction Entry to issue materials your inventory to a work order material 
requirement. Use this function to issue materials to requirements that are not linked to
 purchase orders.

For requirements linked to purchase orders, use Purchase Receipt Entry to create inventory 
transactions. When you receive a linked purchase order, two inventory transactions are 
created. A receipt transaction is created to receive the quantity into inventory. An issue 
transaction to the requirement is then created.

When you issue materials through a manual issue transaction or through a purchase receipt, 
the material requirement completion percentage is updated in the Manufacturing Window. 
If you receive the total required quantity, the material requirement is closed.

Use the Issue function in the main Inventory Transaction window to issue a particular part to a single requirement. 
To issue parts to all requirements, use the Issue By Exception feature. See Using Issue By Exception.

WHEN TYPE = 'I' AND CLASS = 'R' THEN 'Issue Return - General'

Transaction TYPE Values:
Primary Transaction Types:
'I' = Issue (material issued from inventory)
'R' = Receipt (material received into inventory)
'A' = Adjustment (inventory adjustments)
'O' = Other transactions
'IR' = Issue Return (material returned to inventory after being issued)
'RR' = Receipt Return (received material returned/reversed)

Specialized Types:
'T' = Transfer (between locations/warehouses)
'C' = Cycle Count adjustments
'P' = Physical inventory adjustments

Transaction CLASS Values:

Primary Classes:
'R' = Return transactions (reversals)
'A' = Adjustment transactions
'N' = Normal transactions (standard flow)
'M' = Manufacturing/Work Order related
'S' = Sales/Shipping related
'P' = Purchasing/Receiving related
Common TYPE + CLASS Combinations:

CASE     -- Issue Returns    WHEN TYPE = 'IR' AND CLASS = 'R' THEN 'Issue Return - Material Returned to Stock'    
WHEN TYPE = 'I' AND CLASS = 'R' THEN 'Issue Return - General'        -- Receipt Returns      
WHEN TYPE = 'RR' AND CLASS = 'R' THEN 'Receipt Return - WO Receipt Reversed'    
WHEN TYPE = 'R' AND CLASS = 'R' THEN 'Receipt Return - General'        -- Normal Issues    
WHEN TYPE = 'I' AND CLASS = 'M' THEN 'Issue to Manufacturing/Work Order'    
WHEN TYPE = 'I' AND CLASS = 'S' THEN 'Issue for Sales/Shipping'   
WHEN TYPE = 'I' AND CLASS = 'N' THEN 'Issue - Normal'        -- Normal Receipts   
WHEN TYPE = 'R' AND CLASS = 'P' THEN 'Receipt from Purchase Order'    
WHEN TYPE = 'R' AND CLASS = 'M' THEN 'Receipt from Manufacturing/Work Order'   
WHEN TYPE = 'R' AND CLASS = 'N' THEN 'Receipt - Normal'        -- Adjustments    
WHEN TYPE = 'A' AND CLASS = 'A' THEN 'Inventory Adjustment'    
WHEN TYPE = 'A' AND CLASS = 'C' THEN 'Cycle Count Adjustment'    
WHEN TYPE = 'A' AND CLASS = 'P' THEN 'Physical Inventory Adjustment'        -- Transfers    
WHEN TYPE = 'T' AND CLASS = 'N' THEN 'Location/Warehouse Transfer'        
-- Standalone types (when CLASS might be NULL or not specified)    
WHEN TYPE = 'IR' THEN 'Issue Return'    WHEN TYPE = 'RR' THEN 'Receipt Return'    
WHEN TYPE = 'I' THEN 'Issue'    WHEN TYPE = 'R' THEN 'Receipt'    
WHEN TYPE = 'A' THEN 'Adjustment'    WHEN TYPE = 'T' THEN 'Transfer'        -- Catch-all    ELSE TYPE + ' - ' + ISNULL(CLASS, 'N/A')END as TRANSACTION_TYPE_DESCRIPTION
Usage Context:
Returns (CLASS = 'R'):
Issue Returns: Material issued to work orders but returned to stock (unused, excess, defective)
Receipt Returns: Received goods returned to vendor or receipt transaction reversed
Manufacturing (CLASS = 'M'):
Material issued to work orders for production
Finished goods received from completed work orders
Sales/Shipping (CLASS = 'S'):
Material issued for customer shipments
Returns from customers
Purchasing (CLASS = 'P'):
Material received from purchase orders
Vendor returns or receipt reversals
To see the actual values in your system, you could run:


SELECT DISTINCT     TYPE,     CLASS,     COUNT(*) as Count,    MIN(TRANSACTION_DATE) as Earliest,    MAX(TRANSACTION_DATE) as LatestFROM INVENTORY_TRANS WHERE TRANSACTION_DATE >= DATEADD(MONTH, -6, GETDATE())GROUP BY TYPE, CLASSORDER BY TYPE, CLASS;
This will show you the actual TYPE/CLASS combinations used in your system over the last 6 months.

and o.WORKORDER_SUB_ID = ISNULL(a.SUBORD_WO_SUB_ID, 0)



Claude Sonnet 4 • 1x
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
   ,@Part_ID nvarchar(30) = null --'25243C-112 X 11.25 X 68.00' --'65B83903-7' -- '315A6015-14'  -- '287T4518-27' -- 315A6015-14 --  'BACR10AK10C'  -- '212A1214-13'  -- 'BACR10AK10C'
 -- ,@SITE_id nvarchar(30) -- = 'SK01'

 Set @Tester = 0
 --Set @SITE_id = 'SK01'
 DECLARE @workorder_base_id nvarchar(30) = null; -- '1802575' --'1773882'  ---'1789047';  --1801171' ; -- '1793687' -- '1801516'; -- -- '1799404'
dECLARE @Transaction_ID nvarchar(30) = NULL;  --'138481' --  '139140';
DECLARE @TRACE_ID nvarchar(30) = '180971/1'; -- '179473';  -- '183938/1' ;  




--  inventory trans
select  
      t.part_id
    , t.transaction_id
    , t.transaction_date
    , t.class, t.type
    , t.qty, t.costed_qty, t.act_material_cost, t.act_labor_cost
    , t.act_burden_cost, t.act_service_cost
    , t.workorder_base_id
    , t.workorder_lot_id, t.workorder_split_id
    , t.workorder_sub_id, t.operation_seq_no, t.req_piece_no, t.cust_order_id
    , t.cust_order_line_no, t.purc_order_id
    , t.purc_order_line_no, t.warehouse_id
    , t.location_id, w.[description] warehouse_description
    --, l.description
    --, t.description
    ,t.issue_reas_id, t.site_id
    , (case when t.type = 'i' then t.qty else t.qty * -1 end) as effect_on_qty_on_hand
    , ti.trace_id
 --   , ti.TRANSACTION_ID
    , tr.APROPERTY_1 as trace_lot
    -- makes a distinct record that can roll up by trace_id
    , tr.UNAVAILABLE_QTY trace_unavailable_qty
    , tr.IN_QTY as trace_in_qty
    , tr.OUT_QTY as trace_out_qty   

    into #inventory_trans
from inventory_trans t  ---, warehouse w, location l

join [sql-lab-2].live.dbo.warehouse w
on w.id = t.warehouse_id
join [sql-lab-2].live.dbo.[location] l
on w.id = l.warehouse_id 
and t.location_id = l.id 
  LEFT JOIN TRACE_INV_TRANS ti WITH (NOLOCK)
        ON ti.TRANSACTION_ID = t.TRANSACTION_ID 
join PART_WAREHOUSE pw
  ON pw.PART_ID = t.PART_ID
  AND pw.WAREHOUSE_ID = t.WAREHOUSE_ID 



LEFT JOIN TRACE tr WITH (NOLOCK)
  ON tr.ID = ti.TRACE_ID
where 1=1
 --AND TRANSACTION_DATE < @EndDate AND T.PART_ID IS NOT NULL 
--AND T.PART_ID = @Part_ID  
AND ( T.SITE_ID IN ( N'SK01' ) ) 
AND (@TRANSACTION_id IS NULL OR T.TRANSACTION_ID = @TRANSACTION_id) -- Filter by specific transaction ID 
and (ti.trace_id = @TRACE_ID or @TRACE_ID is null)
ORDER BY T.SITE_ID, T.PART_ID, T.TRANSACTION_ID


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
where workorder_base_id = @workorder_base_id or @workorder_base_id IS NULL;


-- select 
--  'inventory_trans' NOTE
-- ,* from inventory_trans t  
-- where workorder_base_id = '1801171';;
-- --@workorder_base_id   -- -- '1793687' -- --'1801516'; -- -- '1799404'

--select STATUS, * from work_order
--where base_id = @workorder_base_id; -- '1801171';  -- '1793687' -- ----  @workorder_base_id   -- -- '1793687' -- '1801516'; -- -- '1799404' -- 1793687

-- select 
--   'TRACE_INV_TRANS' NOTE
--  ,*
-- from TRACE_INV_TRANS
--  where Transaction_ID = @Transaction_ID --  '138481' --  '139140';

-- select 
--  'trace' NOTE
-- ,id, OUT_QTY, IN_QTY, UNAVAILABLE_QTY from TRACE
--  where ID = @TRACE_ID -- --  '183938/1' ;

--  select 
--  'REQ' NOTE
--  ,* from REQUIREMENT
--  where workorder_base_id =  workorder_base_id; -- '1801171'   -- --  '1793687' --  '139140';

-- -- select 1,*
-- --   from INVENTORY_TRANS t WITH (NOLOCK)
-- --   LEFT JOIN TRACE_INV_TRANS ti WITH (NOLOCK)
-- --         ON ti.TRANSACTION_ID = t.TRANSACTION_ID 
-- -- LEFT JOIN TRACE tr WITH (NOLOCK)
-- --   ON tr.ID = ti.TRACE_ID
-- --   where t.Transaction_ID = '138481'
