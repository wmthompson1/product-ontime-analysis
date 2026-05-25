-- Perspective: Engineering
-- Extract master for one part, with operations.
-- The dataset for the master will be used to compare to associated work order. The comparison will identify missing operations or differences in operation details.

-- A master is a salection from work order where ```Work order Type` = 'M'```

/****************************report*****************************************************************
Engineer - Master Operations
William 3/4

-- **********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results;

-- Extract a list of all parts where using Operation_Type for initialization

-- Perspective: Engineering
-- ** Base As Part: ** 
-- pespective ignores this
DECLARE @WorkorderBaseId   varchar(50)  = '313Z7430-504'   -- '5000-6619-001' --  '635TEST-LOS-EME-ALBRKTP';      -- e.g., '5000-6730-001'

DECLARE @WorkorderType     char(1)      = 'M';      -- e.g., 'M'
DECLARE @TEST INT       = 0;        -- 1 = include all operation types, 0 = filter by @OPTYPE
DECLARE @TEST1 INT       = 0; 

-- pespective ignores this
DECLARE @OPTYPE NVARCHAR(MAX) = 'F19.22'; --'02GN089' -- Example: '5793'  NULL. '02GN089'
declare @specs_Different BIT = null;


    SELECT  top 100000
        -- -- Keys (adjust if needed)
        -- o.WORKORDER_BASE_ID
        -- --, ob.WORKORDER_LOT_ID, ob.WORKORDER_SPLIT_ID,
        -- -- ob.WORKORDER_SUB_ID,

        -- ,'x' as note   
        -- , o.WORKORDER_BASE_ID + '-' + o.WORKORDER_lot_ID + '-' + o.WORKORDER_split_ID + '-' + o.WORKORDER_sub_ID AS FULL_LOT_ID
        
        -- ,  ob.WORKORDER_TYPE,   ob.SEQUENCE_NO,
        -- o.OPERATION_TYPE AS OPERATION_TYPE_ID,
        -- o.RESOURCE_ID,

        -- -- Raw binaries
        -- OTB_Bits = otb.BITS,
        -- OB_Bits  = ob.BITS,

        -- -- Your required text view
        -- OTB_Text = CAST(CAST(otb.BITS AS varbinary(max)) AS nvarchar(max)),
        -- OB_Text  = CAST(CAST(ob.BITS  AS varbinary(max)) AS nvarchar(max))
        *
    FROM dbo.OPERATION o

    JOIN dbo.OPERATION_TYPE ot
      ON o.OPERATION_TYPE = ot.ID
    -- AND o.RESOURCE_ID    = ot.RESOURCE_ID

    JOIN dbo.OPER_TYPE_BINARY otb
      ON otb.OPERATION_TYPE_ID = o.OPERATION_TYPE

    JOIN dbo.OPERATION_BINARY ob
      ON ob.WORKORDER_BASE_ID = o.WORKORDER_BASE_ID
     AND ob.WORKORDER_LOT_ID  = o.WORKORDER_LOT_ID
     AND ob.WORKORDER_SPLIT_ID= o.WORKORDER_SPLIT_ID
     AND ob.WORKORDER_SUB_ID  = o.WORKORDER_SUB_ID
     AND ob.WORKORDER_TYPE    = o.WORKORDER_TYPE
     AND ob.SEQUENCE_NO       = o.SEQUENCE_NO


-- join [sql-bi-1].[Staging].[dbo].[Katies_Op_Types] ko
-- on o.OPERATION_TYPE = ko.OPERATION_TYPE_ID


    WHERE 1=1
    -- AND (@WorkorderBaseId IS NULL OR o.WORKORDER_BASE_ID in ( @WorkorderBaseId))
	AND (o.WORKORDER_BASE_ID in ( @WorkorderBaseId)
		    OR @TEST1 = 1)
    -- and o.OPERATION_TYPE in (select id from [SQL-BI-1].[Staging].[dbo].[MyTable])
    -- and ( o.OPERATION_TYPE in (@OPTYPE)
    --   OR @TEST = 1)

    --AND o.OPERATION_TYPE  like '5793'  --'02GN089'
    -- AND (@ResourceId      IS NULL OR o.RESOURCE_ID       = @ResourceId)
      AND ob.WORKORDER_TYPE = @WorkorderType
