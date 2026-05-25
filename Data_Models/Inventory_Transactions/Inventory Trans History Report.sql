
-- Inventory Reports >  Inventory Trans History

declare @PartID nvarchar(255) = '71507E-1100153';

select * from (
	select it.transaction_id 
		, it.transaction_date
		, case when it.class = 'A' and it.transfer_trans_id is not null and it.type = 'I' then 'Transfer In'
			   when it.class = 'A' and it.transfer_trans_id is not null and it.type = 'O' then 'Transfer Out'
			   when it.class = 'A' and it.transfer_trans_id is null and it.type = 'I' then 'Adjust In'
			   when it.class = 'A' and it.transfer_trans_id is null and it.type = 'O' then 'Adjust Out'
			   when it.class = 'R' and it.type = 'I' then 'Receipt'
			   when it.class = 'R' and it.type = 'O' then 'Receipt Rtn'
			   when it.class = 'I' and it.type = 'O' then 'Issue'
			   when it.class = 'I' and it.type = 'I' then 'Issue Rtn'
			   end as TxType
		, it.warehouse_id + '/' + it.location_id as Loc
		, case when it.purc_order_id is not null then 'P ' + it.purc_order_id + '/' + cast(it.purc_order_line_no as varchar)
			   when it.cust_order_id is not null then 'C ' + it.cust_order_id + '/' + cast(it.cust_order_line_no as varchar)
			   when it.workorder_base_id is not null
			   then case when class = 'R' 
						 then it.workorder_base_id + '/' + it.workorder_lot_id + case when it.workorder_split_id = '0' then '' else '.' + it.workorder_split_id end 
						 when class = 'I' 
						 then it.workorder_base_id + '/' + it.workorder_lot_id + case when it.workorder_split_id = '0' then '' else '.' + it.workorder_split_id end 
							+ ' Op# ' + cast(it.operation_Seq_no as varchar) + ' Pc# ' + cast(it.req_piece_no as varchar)
						 end 
			   else '' end as Reference
		, case when units.scale = 0 then cast(it.qty as decimal(28,0)) 
			   when units.scale = 1 then cast(it.qty as decimal(28,1))
			   when units.scale = 2 then cast(it.qty as decimal(28,2))
			   when units.scale = 3 then cast(it.qty as decimal(28,3))
			   when units.scale = 4 then cast(it.qty as decimal(28,4))
			   when units.scale = 5 then cast(it.qty as decimal(28,5))
			   else cast(it.qty as decimal(28,6))
			   end as Qty
		, cast(it.act_material_cost / it.qty as decimal(28,4)) as UnitMatlCost
		, cast(it.act_labor_cost / it.qty as decimal(28,4)) as UnitLabrCost
		, cast(it.act_burden_cost / it.qty as decimal(28,4)) as UnitBurdCost
		, cast(it.act_service_cost / it.qty as decimal(28,4)) as UnitServCost
		, it.description
	from inventory_trans it
	join part p on it.part_id = p.id 
	join units on p.stock_um = units.unit_of_measure 
	where it.part_id = @PartID
	--union all 
	--select it.transaction_id 
	--	, it.transaction_date
	--	, case when it.class = 'A' and it.transfer_trans_id is not null and it.type = 'I' then 'Transfer In'
	--		   when it.class = 'A' and it.transfer_trans_id is not null and it.type = 'O' then 'Transfer Out'
	--		   when it.class = 'A' and it.transfer_trans_id is null and it.type = 'I' then 'Adjust In'
	--		   when it.class = 'A' and it.transfer_trans_id is null and it.type = 'O' then 'Adjust Out'
	--		   when it.class = 'R' and it.type = 'I' then 'Receipt'
	--		   when it.class = 'R' and it.type = 'O' then 'Receipt Rtn'
	--		   when it.class = 'I' and it.type = 'O' then 'Issue'
	--		   when it.class = 'I' and it.type = 'I' then 'Issue Rtn'
	--		   end as TxType
	--	, it.warehouse_id + '/' + it.location_id as Loc
	--	, case when it.purc_order_id is not null then 'P ' + it.purc_order_id + '/' + cast(it.purc_order_line_no as varchar)
	--		   when it.cust_order_id is not null then 'C ' + it.cust_order_id + '/' + cast(it.cust_order_line_no as varchar)
	--		   when it.workorder_base_id is not null
	--		   then case when class = 'R' 
	--					 then it.workorder_base_id + '/' + it.workorder_lot_id + case when it.workorder_split_id = '0' then '' else '.' + it.workorder_split_id end 
	--					 when class = 'I' 
	--					 then it.workorder_base_id + '/' + it.workorder_lot_id + case when it.workorder_split_id = '0' then '' else '.' + it.workorder_split_id end 
	--						+ ' Op# ' + cast(it.operation_Seq_no as varchar) + ' Pc# ' + cast(it.req_piece_no as varchar)
	--					 end 
	--		   else '' end as Reference
	--	, case when units.scale = 0 then cast(it.qty as decimal(28,0)) 
	--		   when units.scale = 1 then cast(it.qty as decimal(28,1))
	--		   when units.scale = 2 then cast(it.qty as decimal(28,2))
	--		   when units.scale = 3 then cast(it.qty as decimal(28,3))
	--		   when units.scale = 4 then cast(it.qty as decimal(28,4))
	--		   when units.scale = 5 then cast(it.qty as decimal(28,5))
	--		   else cast(it.qty as decimal(28,6))
	--		   end as Qty
	--	, cast(it.act_material_cost / it.qty as decimal(28,4)) as UnitMatlCost
	--	, cast(it.act_labor_cost / it.qty as decimal(28,4)) as UnitLabrCost
	--	, cast(it.act_burden_cost / it.qty as decimal(28,4)) as UnitBurdCost
	--	, cast(it.act_service_cost / it.qty as decimal(28,4)) as UnitServCost
	--	, it.description
	--from LIVEARC.dbo.inventory_trans it
	--join part p on it.part_id = p.id 
	--join units on p.stock_um = units.unit_of_measure 
	--where it.part_id = @PartID
)q order by transaction_date DESC