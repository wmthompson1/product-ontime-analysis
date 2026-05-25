-- S1.2.1.1 Inventory_Transactions_Filtered.sql
-- file path: SQL_Reports/Inventory/Inventory - Transactions AI Review.sql
-- run at sql-lab-2 in prod
-- dw in stage on sql-bi-1



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
12/12/25    William Thompson    Updated for Code Base S1.2.1.1 part_id used in join 

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

Use the Issue function in the main Inventory Transaction window to issue a particular part to a single requirement. To issue parts to all requirements, use the Issue By Exception feature. See Using Issue By Exception.

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

CASE     -- Issue Returns    WHEN TYPE = 'IR' AND CLASS = 'R' THEN 'Issue Return - Material Returned to Stock'    WHEN TYPE = 'I' AND CLASS = 'R' THEN 'Issue Return - General'        -- Receipt Returns      WHEN TYPE = 'RR' AND CLASS = 'R' THEN 'Receipt Return - WO Receipt Reversed'    WHEN TYPE = 'R' AND CLASS = 'R' THEN 'Receipt Return - General'        -- Normal Issues    WHEN TYPE = 'I' AND CLASS = 'M' THEN 'Issue to Manufacturing/Work Order'    WHEN TYPE = 'I' AND CLASS = 'S' THEN 'Issue for Sales/Shipping'    WHEN TYPE = 'I' AND CLASS = 'N' THEN 'Issue - Normal'        -- Normal Receipts    WHEN TYPE = 'R' AND CLASS = 'P' THEN 'Receipt from Purchase Order'    WHEN TYPE = 'R' AND CLASS = 'M' THEN 'Receipt from Manufacturing/Work Order'    WHEN TYPE = 'R' AND CLASS = 'N' THEN 'Receipt - Normal'        -- Adjustments    WHEN TYPE = 'A' AND CLASS = 'A' THEN 'Inventory Adjustment'    WHEN TYPE = 'A' AND CLASS = 'C' THEN 'Cycle Count Adjustment'    WHEN TYPE = 'A' AND CLASS = 'P' THEN 'Physical Inventory Adjustment'        -- Transfers    WHEN TYPE = 'T' AND CLASS = 'N' THEN 'Location/Warehouse Transfer'        -- Standalone types (when CLASS might be NULL or not specified)    WHEN TYPE = 'IR' THEN 'Issue Return'    WHEN TYPE = 'RR' THEN 'Receipt Return'    WHEN TYPE = 'I' THEN 'Issue'    WHEN TYPE = 'R' THEN 'Receipt'    WHEN TYPE = 'A' THEN 'Adjustment'    WHEN TYPE = 'T' THEN 'Transfer'        -- Catch-all    ELSE TYPE + ' - ' + ISNULL(CLASS, 'N/A')END as TRANSACTION_TYPE_DESCRIPTION
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


REQUIREMENT.CALC_QTY is the Required Quantity for the part 

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

declare @part_id nvarchar(250) = '313Z7430-504';  -- '313Z7430-504' '70750B-071-MIL-NG';


Set @Tester = 0
--Set @SITE_id = 'SK01'
DECLARE @workorder_base_id nvarchar(30) = '1803245' -- '1802575' --'1789047'; --'1670717'; -- '1801171'; -- '1793687'


select
  'work order operations' note
, a.part_id

--, r.calc_qty required_qty  -- material requirement
, a.status workorder_status
, a.base_id
, a.lot_id
, a.split_id
, a.sub_id
, o.SEQUENCE_NO

    , o.RESOURCE_ID
    ,P.STOCK_UM

-- inventory transaction flow

  from dbo.WORK_ORDER a
--   on i.WORKORDER_BASE_ID=a.BASE_ID
--     and i.WORKORDER_LOT_ID=a.LOT_ID and
--     i.WORKORDER_SPLIT_ID = a.SPLIT_ID
--     and i.WORKORDER_SUB_ID = a.SUB_ID


  INNER JOIN OPERATION o
  on o.WORKORDER_BASE_ID=a.BASE_ID and o.WORKORDER_LOT_ID=a.LOT_ID and
    o.WORKORDER_SPLIT_ID = a.SPLIT_ID
    and o.WORKORDER_SUB_ID = a.SUB_ID

-- -- materials requirement flow (subordinate work order link)
--   inner join REQUIREMENT r WITH (NOLOCK)
--   on i.part_id = r.part_id
--     and o.WORKORDER_BASE_ID=r.WORKORDER_BASE_ID and o.WORKORDER_LOT_ID=r.WORKORDER_LOT_ID and
--     o.WORKORDER_SPLIT_ID = r.WORKORDER_SPLIT_ID and o.SEQUENCE_NO = r.OPERATION_SEQ_NO
--     and o.WORKORDER_SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)

  Inner Join PART P  with (nolock) on a.PART_ID = P.ID

where 1=1
  --and i.warehouse_id = 'Auburn Mtl Cage'
  AND (a.base_id = @workorder_base_id OR @workorder_base_id IS NULL)
  --and a.STATUS not in ('X', 'C')
  and a.STATUS in ('R', 'E', 'H', 'S', 'P', 'F','C')  -- Released, Enroute, Hold, Started, Partially Complete, Finished,Closed

  and (a.part_id = @Part_ID
  or @Part_ID IS NULL )
order by a.BASE_ID, a.LOT_ID