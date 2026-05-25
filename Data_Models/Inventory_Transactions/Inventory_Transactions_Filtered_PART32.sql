-- this file name: Inventory_Transactions_Filtered_PART32.sql 
-- Documentation\Schema\Data_Models\Inventory_Transactions\Inventory_Transactions_Filtered_PART32.sql
-- is meant to be represent material requirements and unissued. but importantly the part id for components can be the unresolved REWORK MFG,
-- breaaak down inventory ransactions filtered script (this to include only workorder and requirement tables, joined to get the material requirement flow
-- material requirements are child records while the subcomponts needto join to work order daily status flow.
--Summary: 
--  1. render cild records for material requireemnt 
--  2. provide join to work order to align parent (subcomponent) to child (material requirement) flow
--  3. include the unresolved REWORK MFG part id to be able to link

-- Work Order Reports\WorkOrderDailyStatus>
--  ├── 40 Raw material avail
	/* script 2  */
	-- material_top_level.sql


-- test # 1: work order base id  1789451 is closed now but proides a good test case, having 2 subcomponents, one of which was reworked (sub component 3)   
DECLARE @Tester int
  -- ,@Part_ID nvarchar(30) =  null; -- '71507E-1100153'
declare @part_id nvarchar(250) = null; --'BACN11G3A7CD';  -- '70750B-071-MIL-NG';

/**  work order left join this_set) **/
Set @Tester = 0
--Set @SITE_id = 'SK01'
DECLARE  
 		    @workorder_TYPE 		nchar(1) = 'W'
           ,@workorder_BASE_ID 	nvarchar(30) =   '1789451'  -- 1808412
           ,@workorder_LOT_ID 	nvarchar(3) = NULL
           ,@workorder_SPLIT_ID 	nvarchar(3) = NULL
           ,@workorder_SUB_ID 	nvarchar(3) = '0'

select
        CASE 
        WHEN a.PART_ID like '%REWORK%' THEN 
          (	SELECT PART_ID FROM WORK_ORDER w 
            WHERE w.[TYPE] = a.[TYPE] AND w.BASE_ID = a.BASE_ID 
            AND w.LOT_ID = a.LOT_ID AND w.SPLIT_ID = a.SPLIT_ID 
            AND w.SUB_ID = N'0' AND w.PART_ID <> N'REWORK MFG'
          )
        ELSE a.PART_ID 
      END as EndItem_Part_id
      , a.BASE_ID, a.LOT_ID, a.SPLIT_ID
      , r.PART_ID AS PART_ID
      , r.SUBORD_WO_SUB_ID, a.[TYPE]
      , r.WORKORDER_SUB_ID
      , r.ISSUED_QTY
      , R.CALC_QTY

  , a.DESIRED_QTY, a.[STATUS]
 
  , r.OPERATION_SEQ_NO

  -- 1807646/1 Op# 20 Pc# 30
  , reference = ISNULL(r.WORKORDER_BASE_ID,N'') + '/' + ISNULL(r.WORKORDER_LOT_ID,N'')   + SPACE(1) 
     + 'Op# ' + ISNULL(CONVERT(NVARCHAR(30), r.OPERATION_SEQ_NO), N'') + SPACE(1) 
     + 'Pc# ' + ISNULL(CONVERT(NVARCHAR(30), r.PIECE_NO), N'')  

  FROM dbo.WORK_ORDER a
-- -- --  materials requirement flow (subordinate work order link)
  inner join REQUIREMENT r WITH (NOLOCK)
  on  --a.PART_ID = r.PART_ID
     a.BASE_ID=r.WORKORDER_BASE_ID and a.LOT_ID=r.WORKORDER_LOT_ID and
    a.SPLIT_ID = r.WORKORDER_SPLIT_ID and r.OPERATION_SEQ_NO = r.OPERATION_SEQ_NO

-- -- -- the constrained sets allow naterial requirements flow to join to work order including join on r.workorder_sub_id 
    and a.SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)
    -- -- 2 of 2 constraints 
    and (r.WORKORDER_SUB_ID = 0 and r.SUBORD_WO_SUB_ID is null)
    
  -- -- -- lower level defined as: 
  -- -- -- lower level child record, can be material requirement or subcomponent depending on the level, but we want 
  -- -- -- to exclude the parent record which has no material requirement or subcomponent link
  --   and a.SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)
  --   -- 2 of 2 constraints 
  --   and not (r.WORKORDER_SUB_ID = 0 and r.SUBORD_WO_SUB_ID is null)
  --   -- 3rd constraint child only
  --   and r.SUBORD_WO_SUB_ID is null



where 1=1
 and a.[TYPE] = @workorder_TYPE
 AND (a.BASE_ID = @workorder_BASE_ID OR @workorder_BASE_ID IS NULL)
 and a.STATUS in ('R', 'E', 'H', 'S', 'P', 'F','C')  -- Released, Enroute, Hold, Started, Partially Complete, Finished,Closed

  and (a.PART_ID = @Part_ID
  or @Part_ID IS NULL )
order by a.BASE_ID --,a.SUB_ID, r.OPERATION_SEQ_NO