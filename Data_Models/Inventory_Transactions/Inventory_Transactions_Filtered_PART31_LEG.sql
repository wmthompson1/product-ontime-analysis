--Inventory_Transactions_Filtered_PART3_LEG
/**
1805209-1/1
MS20257X5-530

**/

-- this file name: Inventory_Transactions_Filtered_PART2.sql is meant to be run after Inventory_Transactions_Filtered_PART1.sql

DECLARE @Tester int
  -- ,@Part_ID nvarchar(30) =  null; -- '71507E-1100153'
declare @part_id nvarchar(250) = null; --'BACN11G3A7CD';  -- '70750B-071-MIL-NG';
--'25243C-112 X 11.25 X 68.00' --'65B83903-7' -- '315A6015-14'  -- '287T4518-27' -- 315A6015-14 --  'BACR10AK10C'  -- '212A1214-13'  -- 'BACR10AK10C'
-- ,@SITE_id nvarchar(30) -- = 'SK01'

Set @Tester = 0
--Set @SITE_id = 'SK01'
DECLARE  
 		    @workorder_TYPE 		nchar(1) = 'W'
           ,@workorder_BASE_ID 	nvarchar(30) = '1808412' -- '1805209'/1  ---  '1807646'
           ,@workorder_LOT_ID 	nvarchar(3) = NULL
           ,@workorder_SPLIT_ID 	nvarchar(3) = NULL
           ,@workorder_SUB_ID 	nvarchar(3) = '1'
;


select
 a.BASE_ID, a.LOT_ID, a.SPLIT_ID, a.SUB_ID, a.[TYPE]
  , CASE 
    WHEN a.PART_ID = N'REWORK MFG' THEN 
      (	SELECT PART_ID FROM WORK_ORDER w 
        WHERE w.[TYPE] = a.[TYPE] AND w.BASE_ID = a.BASE_ID 
        AND w.LOT_ID = a.LOT_ID AND w.SPLIT_ID = a.SPLIT_ID 
        AND w.SUB_ID = N'0' AND w.PART_ID <> N'REWORK MFG'
      )
    ELSE a.PART_ID 
  END PART_ID
 --- , dbo.sfnWONUMFormat(a.BASE_ID, a.LOT_ID, a.SPLIT_ID, a.SUB_ID) AS 'WONUM'
  , a.DESIRED_QTY, a.[STATUS]
 
  , o.SEQUENCE_NO
  -- 1807646/1 Op# 20 Pc# 30
  , reference = ISNULL(r.WORKORDER_BASE_ID,N'') + '/' + SPACE(1)
     + 'Op# ' + ISNULL(CONVERT(NVARCHAR(30), r.OPERATION_SEQ_NO), N'') + SPACE(1) 
     + 'Pc# ' + ISNULL(CONVERT(NVARCHAR(30), r.PIECE_NO), N'')  
   , r.PART_ID AS REQ_PART_ID
   ,r.SUBORD_WO_SUB_ID

  FROM dbo.WORK_ORDER a

  INNER JOIN OPERATION o
  on o.WORKORDER_BASE_ID=a.BASE_ID and o.WORKORDER_LOT_ID=a.LOT_ID and
    o.WORKORDER_SPLIT_ID = a.SPLIT_ID
    and o.WORKORDER_SUB_ID = a.SUB_ID

-- 
-- -- --  materials requirement flow (subordinate work order link)
  inner join REQUIREMENT r WITH (NOLOCK)
  on  --a.PART_ID = r.PART_ID
     o.WORKORDER_BASE_ID=r.WORKORDER_BASE_ID and o.WORKORDER_LOT_ID=r.WORKORDER_LOT_ID and
    o.WORKORDER_SPLIT_ID = r.WORKORDER_SPLIT_ID and o.SEQUENCE_NO = r.OPERATION_SEQ_NO
 and o.WORKORDER_SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)
    --and o.WORKORDER_SUB_ID = (r.WORKORDER_SUB_ID)

  --Inner Join PART P  with (nolock) on R.PART_ID = P.ID

where 1=1
 and a.[TYPE] = @workorder_TYPE
--   --and i.warehouse_id = 'Auburn Mtl Cage'
AND (a.BASE_ID = @workorder_BASE_ID OR @workorder_BASE_ID IS NULL)
--   --and a.STATUS not in ('X', 'C')
  and a.STATUS in ('R', 'E', 'H', 'S', 'P', 'F','C')  -- Released, Enroute, Hold, Started, Partially Complete, Finished,Closed

  and (a.PART_ID = @Part_ID
  or @Part_ID IS NULL )
order by a.STATUS_EFF_DATE desc, a.BASE_ID, a.LOT_ID