--  Raw Materials> RM_Location_WO

declare @W_O varchar(50) = '1803286'  -- Enter Work Order or 'All' for all work orders

Select R.WORKORDER_BASE_ID as 'WO'
,R.WORKORDER_LOT_ID as 'LOT'
,R.WORKORDER_SPLIT_ID as 'SPLIT'
,WORKORDER_SUB_ID as 'SUB_ID'
,R.PART_ID, R.CALC_QTY
,t.WAREHOUSE_ID, t.Location_ID
, t.Stock
,P.STOCK_UM, T.TRACE_ID
,x.APROPERTY_2 Trace_Lot
from REQUIREMENT R with (nolock)
Inner Join PART P  with (nolock) on R.PART_ID = P.ID
Left Join (
	select t.PART_ID, i.WAREHOUSE_ID, i.LOCATION_ID, SUM(t.QTY) as 'Stock', t.TRACE_ID
	from TRACE_INV_TRANS t with (nolock) inner join INVENTORY_TRANS i with (nolock)
	on t.TRANSACTION_ID = i.TRANSACTION_ID
	group by t.PART_ID, i.WAREHOUSE_ID, i.LOCATION_ID, t.TRACE_ID
	having SUM(t.QTY) > 0 
) t on R.PART_ID = t.PART_ID and P.ID = t.PART_ID
 JOIN TRACE x ON t.trace_ID = x.ID
 AND t.PART_ID = x.PART_ID

where 1=1
and ( R.WORKORDER_BASE_ID = @W_O 
          or @W_O = 'All')

and 
P.COMMODITY_CODE in ('Standards', 'Raw Material')
and t.WAREHOUSE_ID = 'Auburn Mtl Cage'
Order by t.LOCATION_ID