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
        Whether or not all transactions trace does not impact1 test,
        but rather allows a dataset to render the difference in transaction
        in case the is a variance with the amounts.    
Code Base: 3.2.4 Inventory - On Hand Reconciled    

Date        Modified By         Change Description
----------  ------------------  ------------------------------------------------------------
08/03/20    William Thompson    Created.
12/10/25    William Thompson    Updated for Code Base 3.2.4 - Determine location of parts 

### Scenario Matrix

From the attached specification and database analysis:

| Scenario | Class | Type | Class Tag | Type Tag | Effect on QOH | Database Query Pattern |
|----------|-------|------|-----------|----------|---------------|------------------------|
| 1 | R | I | Released | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'R'` |
| 2 | A | O | Adjust | Out | `-1 * QTY` | `TYPE = 'O' AND CLASS = 'A'` |
| 3 | A | I | Adjust | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'A'` |
| 4 | I | O | Issue | Out | `-1 * QTY` | `TYPE = 'O' AND CLASS = 'I'` |
| 5 | I | I | Issue | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'I'` |

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

IF OBJECT_ID('tempdb..#Inventory_On_Hand_Reconcilable') IS NOT NULL DROP TABLE #Inventory_On_Hand_Reconcilable

IF OBJECT_ID('tempdb..#temp1') IS NOT NULL DROP TABLE #temp1
IF OBJECT_ID('tempdb..#temp2') IS NOT NULL DROP TABLE #temp2
IF OBJECT_ID('tempdb..#temp3') IS NOT NULL DROP TABLE #temp3
IF OBJECT_ID('tempdb..#temp4') IS NOT NULL DROP TABLE #temp4
IF OBJECT_ID('tempdb..#temp5') IS NOT NULL DROP TABLE #temp5


DECLARE @Tester int
   ,@Part_ID nvarchar(30) = '20240C-063' 
 
 ,@TRANSACTION_id nvarchar(30) = NULL  
 
 Set @Tester = 0
 

SELECT 
'trace_profile' note,
 [PART_ID]
 ,t.APPLY_TO_ADJ,t.APPLY_TO_ISSUE,t.APPLY_TO_LABOR,t.APPLY_TO_SERVDISP,t.APPLY_TO_SERVREC
,TRACE_ID_LABEL, APROPERTY_1_REQD, APROPERTY_2_REQD, APROPERTY_3_REQD
, APROPERTY_4_REQD, APROPERTY_5_REQD, APROPERTY_LABEL_1, APROPERTY_LABEL_2
, APROPERTY_LABEL_3, APROPERTY_LABEL_4, APROPERTY_LABEL_5, NPROPERTY_1_REQD
, NPROPERTY_2_REQD, NPROPERTY_3_REQD, NPROPERTY_4_REQD, NPROPERTY_5_REQD
, NPROPERTY_LABEL_1, NPROPERTY_LABEL_2, NPROPERTY_LABEL_3, NPROPERTY_LABEL_4, NPROPERTY_LABEL_5
, APROPERTY_1_EDIT, APROPERTY_2_EDIT, APROPERTY_3_EDIT, APROPERTY_4_EDIT, APROPERTY_5_EDIT
, NPROPERTY_1_EDIT, NPROPERTY_2_EDIT, NPROPERTY_3_EDIT, NPROPERTY_4_EDIT, NPROPERTY_5_EDIT
, APROPERTY_1_VIS, APROPERTY_2_VIS, APROPERTY_3_VIS, APROPERTY_4_VIS, APROPERTY_5_VIS
, NPROPERTY_1_VIS, NPROPERTY_2_VIS, NPROPERTY_3_VIS, NPROPERTY_4_VIS, NPROPERTY_5_VIS
, EDIT_EXP_DATE, [OWNERSHIP], SERIAL, LOT, PRODUCTION, RECEIVE_BY, AVAILABLE, SHIP_BY, EXPIRATION 
  into #trace_profile
FROM live.dbo.TRACE_PROFILE t
WHERE (PART_ID = @PART_id OR @PART_id IS NULL)




Create clustered index ci_tp12 on #trace_profile (part_id)



SELECT 
    'trace' note,
  id, part_id
, serial_id, lot_id, owner_id, in_qty, out_qty
, net_qty = in_qty - out_qty
, reported_qty, assigned_qty, numbering_id, aproperty_1, aproperty_2, aproperty_3
, aproperty_4, aproperty_5, nproperty_1, nproperty_2, nproperty_3, nproperty_4, nproperty_5
, comments, production_date, receive_by_date, available_date, ship_by_date, expiration_date, disp_in_qty
, disp_out_qty, committed_qty 
  into #Trace
FROM TRACE T  
WHERE (T.PART_ID = @Part_id OR @Part_id IS NULL)
ORDER BY PART_ID, ID 




SELECT 
    ID, PART_ID, SERIAL_ID, LOT_ID, OWNER_ID, IN_QTY, OUT_QTY 
    , net_qty = IN_QTY - OUT_QTY
    , REPORTED_QTY, ASSIGNED_QTY
    , NUMBERING_ID, APROPERTY_1, APROPERTY_2, APROPERTY_3, APROPERTY_4, APROPERTY_5, NPROPERTY_1, NPROPERTY_2, NPROPERTY_3
    , NPROPERTY_4, NPROPERTY_5, COMMENTS, PRODUCTION_DATE, RECEIVE_BY_DATE, AVAILABLE_DATE, SHIP_BY_DATE, EXPIRATION_DATE
    , DISP_IN_QTY, DISP_OUT_QTY, COMMITTED_QTY
 into #part_trace_maint
 FROM TRACE T 
 WHERE (1=1)
and PART_ID = @PART_ID 
            and ( t.id in ( 
            select distinct v.trace_id 
            from trace_inv_trans v, inventory_trans i 
        
            where v.part_id = t.part_id 
            and v.part_id = i.part_id and i.site_id = 'SK01'
            and (@TRANSACTION_id IS NULL OR i.TRANSACTION_ID = @TRANSACTION_id))

             or t.id in (
              select distinct ( x.trace_id ) from [sql-lab-2].live.dbo.trace_labor_trans x
              , labor_ticket l, work_order w 
               where w.part_id = t.part_id 
               and x.transaction_id = l.transaction_id 
               and l.site_id =  'SK01' 
               and w.base_id = l.workorder_base_id 
               and w.lot_id = l.workorder_lot_id 
               and w.split_id = l.workorder_split_id 
               and w.sub_id = l.workorder_sub_id 
               and w.[type] = l.workorder_type ) or ( t.assigned_qty >= 0 and t.out_qty = 0 
               and t.in_qty = 0 ) ) order by part_id, id



select 
    'trace_inv_trans' note, x.qty, t.workorder_type
    ,t.workorder_base_id, t.workorder_lot_id
    ,t.workorder_split_id, t.workorder_sub_id, t.operation_seq_no, t.req_piece_no, t.purc_order_id
    ,t.purc_order_line_no, t.cust_order_id, t.cust_order_line_no, t.transaction_date
    ,t.type, t.class, t.warehouse_id, t.location_id 
    ,x.part_id
    ,x.trace_id
    ,x.transaction_id
  into #trace_inv_trans
from trace_inv_trans x
join inventory_trans t 
on x.transaction_id = t.transaction_id 
and t.site_id = 'SK01' 

where x.part_id = t.part_id
AND (@TRANSACTION_id IS NULL OR t.TRANSACTION_ID = @TRANSACTION_id) 
 

ORDER BY T.TRANSACTION_DATE, T.TRANSACTION_ID



create clustered index [ci_x_tra_inv_trans_12] on #trace_inv_trans
(   part_id,
    trace_id,
    transaction_id
)




select
    sum(qty) qty
   ,tx.part_id
   ,tx.[transaction_id]
   into #tixact_agg_by_xact_id
from #trace_inv_trans tx
group by 
    tx.part_id
    ,tx.transaction_id




select
    sum(qty) qty
   ,tx.part_id
   ,tx.[transaction_id]
   into #tixact_agg_by_part_id
from #tixact_agg_by_xact_id tx
group by 
    tx.part_id
    ,tx.transaction_id









create clustered index [ci_tixact_aggs_12] on #tixact_agg_by_xact_id
(
    part_id,
    transaction_id
)


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
    
    
    ,t.issue_reas_id, t.site_id
    , (case when t.type = 'i' then t.qty else t.qty * -1 end) as effect_on_qty_on_hand
    into #inventory_trans
from inventory_trans t  
join [sql-lab-2].live.dbo.warehouse w
on w.id = t.warehouse_id
join [sql-lab-2].live.dbo.[location] l
on w.id = l.warehouse_id 
and t.location_id = l.id  

 

AND ( T.SITE_ID IN ( N'SK01' ) ) 
AND (@TRANSACTION_id IS NULL OR T.TRANSACTION_ID = @TRANSACTION_id) 
ORDER BY T.SITE_ID, T.PART_ID, T.TRANSACTION_ID



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



select 
  ixact.PART_ID
  ,tx_agg.PART_ID txact_PART_id
  ,ixact.TRANSACTION_ID
  ,ixact.EFFECT_ON_QTY_ON_HAND
  ,tx_agg.QTY
  into #results
FROM #inventory_trans ixact
join PART p
on ixact.PART_ID = p.id

JOIN [sql-lab-2].[live].dbo.TRACE_PROFILE TP
    ON ixact.PART_ID = TP.PART_ID

left join #tixact_agg_by_xact_id tx_agg
on ixact.TRANSACTION_ID = tx_agg.TRANSACTION_ID
and ixact.PART_ID =tx_agg.PART_ID

where isnull(p.status,'') != 'O'



select 
     part_id, sum(effect_on_qty_on_hand) effect_on_qty_on_hand 
     into #ixact_agg_by_part
from #inventory_trans

group by part_id


















select 
   'tst 1227'   as test_label,
   r.part_id
  ,r.txact_part_id
 
  ,sum(r.effect_on_qty_on_hand) effect_on_qty_on_hand
  ,sum(r.qty) qty
  into #results_agg
from #results r
join part p
on r.part_id = p.id

JOIN [sql-lab-2].[live].dbo.TRACE_PROFILE TP
    ON r.PART_ID = TP.PART_ID
where isnull(p.status,'') != 'O'
group by
   r.PART_ID
  ,r.txact_PART_id











profile_ix:

































SELECT 
      pl.PART_ID
    , ISNULL ( SUM ( PL.QTY ), 0 ) QTY
   into #planning_on_hand
FROM PART_LOCATION PL
JOIN [sql-lab-2].[live].dbo.WAREHOUSE W 
ON PL.WAREHOUSE_ID = W.ID 
join [sql-lab-2].[live].dbo.TRACE_PROFILE tp
on pl.PART_ID = tp.PART_ID
join part p
on p.id = pl.PART_ID
WHERE (1=1)
and isnull(p.status,'') != 'O'
and (PL.PART_ID = @part_id OR @part_id IS NULL)
AND W.SITE_ID = 'SK01' 
group by pl.PART_ID



select *
   into #temp1
FROM (
select
 r.PART_ID
 ,r.qty
 ,oh.qty oh_qty
 , r.qty - oh.qty Variance

from #results_agg r
join #planning_on_hand oh
on r.PART_ID = oh.PART_ID
) AS V

render_chosen_dataset1:




select 
  t.*
  into #temp2
from (
select
    ix.part_id, ix.effect_on_qty_on_hand  ix_qty
    ,poh.qty oh_qty
    ,tx.qty tx_qty

from #ixact_agg_by_part ix


join
 (
 select part_id, sum(qty) qty from  #tixact_agg_by_part_id tx group by part_id

 ) tx
 on ix.PART_ID = tx.PART_ID


join #planning_on_hand poh
on ix.PART_ID = poh.PART_ID
) t




select *
  into #temp3
FROM #temp2
WHERE IX_QTY = OH_QTY
  AND OH_QTY = TX_QTY
  AND TX_QTY = IX_QTY
ORDER BY part_id










profile_part_reconcile:











































































































































































CREATE TABLE #Inventory_On_Hand_Reconcilable(










    [PART_ID] [nvarchar](30) NULL,
    [DESCRIPTION] [nvarchar](120) NULL,
    [inv_xactn] [decimal](38, 4) NULL,
    [on_hand] [decimal](38, 4)  NULL,
    [trace_xactn] [decimal](38, 4) NULL,
    [Is_Reconciled] [varchar](1)  NULL,
    [status] [nchar](1) NULL,
    [MRP_REQUIRED] [nchar](1) NULL,
    [commodity_code] [nvarchar](15) NULL,
    [STOCK_UM] [nvarchar](15)  NULL,
    [FABRICATED] [nchar](1)  NULL,
    [PURCHASED] [nchar](1)  NULL,
    [STOCKED] [nchar](1)  NULL,
    [MRP_EXCEPTIONS] [nchar](1) NULL,

    [DWRowInsertDate] [datetime2](7) NOT NULL DEFAULT (sysdatetime()),
    [DWRowUpdateDate] [datetime2](7) NOT NULL DEFAULT (sysdatetime())
)  










    

INSERT INTO #Inventory_On_Hand_Reconcilable
           (
            [PART_ID]
           ,[DESCRIPTION]
           ,[inv_xactn]
           ,[on_hand]
           ,[trace_xactn]
           ,[Is_Reconciled]
           ,[status]
           ,[MRP_REQUIRED]
           ,[commodity_code]
           ,[STOCK_UM]
           ,[FABRICATED]
           ,[PURCHASED]
           ,[STOCKED]
           ,[MRP_EXCEPTIONS]
           
           
           )

 select 
    t.PART_ID,p.[DESCRIPTION] 
  , t.ix_qty inv_xactn
  , t.oh_qty on_hand 
  , t.tx_qty trace_xactn
  , Is_Reconciled = case 
  when IX_QTY = OH_QTY
  AND OH_QTY = TX_QTY
  AND TX_QTY = IX_QTY then
    'Y'
  ELSE
    'N' END

  , p.status, MRP_REQUIRED, p.commodity_code, p.STOCK_UM, p.FABRICATED
  , p.PURCHASED, p.STOCKED, MRP_EXCEPTIONS
 
 
from #temp2 t
join part p
on t.PART_ID = p.id
order by part_id




























select 
'1.1 inventory_trans filter' note
,* from #inventory_trans
where 
(part_id = @Part_ID
or @Part_ID IS NULL )
AND (@TRANSACTION_id IS NULL OR TRANSACTION_ID = @TRANSACTION_id) 



    
    

    
    AND TRANSACTION_DATE >= cast(convert(date,'2025-01-20') as datetime)  
    AND TRANSACTION_DATE < cast(convert(date,'2025-01-21') as datetime)


