-- Perspective: Engineering
-- Extract master for one part, with operations.
-- The dataset for the master will be used to compare to associated work order. The comparison will identify missing operations or differences in operation details.

-- A master is a salection from work order where ```Work order Type` = 'M'```

/****************************report*****************************************************************
Engineer - Master Construction
William 3/4

-- **********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results;

-- Extract a list of all parts where using Operation_Type for initialization

-- Perspective: Engineering
-- ** Base As Part: ** 
-- pespective ignores this
DECLARE @WorkorderBaseId   varchar(50)  = '1803245'; --'313Z7430-504'   -- '5000-6619-001' --  '635TEST-LOS-EME-ALBRKTP';      -- e.g., '5000-6730-001'
DECLARE @SPLIT_ID NVARCHAR(3) = N'3';
DECLARE @WorkorderType     char(1)      = 'W';      -- e.g., 'M'
DECLARE @TEST INT       = 0;        -- 1 = include all operation types, 0 = filter by @OPTYPE
DECLARE @TEST1 INT       = 0; 

-- pespective ignores this
DECLARE @OPTYPE NVARCHAR(MAX) = 'F19.22'; --'02GN089' -- Example: '5793'  NULL. '02GN089'
declare @specs_Different BIT = null;

;WITH J AS
(
    SELECT  top 100000
        -- Keys (adjust if needed)
        o.WORKORDER_BASE_ID
        ,o.WORKORDER_split_ID 
        --, ob.WORKORDER_LOT_ID, ob.WORKORDER_SPLIT_ID,
        -- ob.WORKORDER_SUB_ID,

        ,'x' as note   
        , o.WORKORDER_BASE_ID + '-' + o.WORKORDER_lot_ID + '-' + o.WORKORDER_split_ID + '-' + o.WORKORDER_sub_ID AS FULL_LOT_ID
        
        ,  ob.WORKORDER_TYPE,   ob.SEQUENCE_NO,
        o.OPERATION_TYPE AS OPERATION_TYPE_ID,
        o.RESOURCE_ID,

        -- Raw binaries
        OTB_Bits = otb.BITS,
        OB_Bits  = ob.BITS,

        -- Your required text view
        OTB_Text = CAST(CAST(otb.BITS AS varbinary(max)) AS nvarchar(max)),
        OB_Text  = CAST(CAST(ob.BITS  AS varbinary(max)) AS nvarchar(max))
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
    AND o.WORKORDER_SPLIT_ID = @SPLIT_ID
    -- and o.OPERATION_TYPE in (select id from [SQL-BI-1].[Staging].[dbo].[MyTable])
    -- and ( o.OPERATION_TYPE in (@OPTYPE)
    --   OR @TEST = 1)

    --AND o.OPERATION_TYPE  like '5793'  --'02GN089'
    -- AND (@ResourceId      IS NULL OR o.RESOURCE_ID       = @ResourceId)
      AND ob.WORKORDER_TYPE = @WorkorderType
),
Tails AS
(
    -- Compute trailing CR/LF length and body for both sides.
    -- We only care about the tail composed of CHAR(13)/CHAR(10).
    SELECT
        J.*,

        -- Reverse strings to find the first non-CR/LF from the right
        OTB_Rev = REVERSE(J.OTB_Text),
        OB_Rev  = REVERSE(J.OB_Text)
    FROM J
),
Cuts AS
(
    SELECT
        T.*,

        OTB_FirstNon = NULLIF(PATINDEX('%[^' + CHAR(13) + CHAR(10) + ']%', T.OTB_Rev), 0),
        OB_FirstNon  = NULLIF(PATINDEX('%[^' + CHAR(13) + CHAR(10) + ']%', T.OB_Rev ), 0)
    FROM Tails AS T
),
Bodies AS
(
    SELECT
        C.*,

        OTB_TrailingLen = CASE 
                            WHEN C.OTB_Text IS NULL THEN NULL
                            WHEN C.OTB_FirstNon IS NULL THEN LEN(C.OTB_Text)        -- all CR/LF
                            ELSE C.OTB_FirstNon - 1
                          END,
        OB_TrailingLen  = CASE 
                            WHEN C.OB_Text IS NULL THEN NULL
                            WHEN C.OB_FirstNon IS NULL THEN LEN(C.OB_Text)           -- all CR/LF
                            ELSE C.OB_FirstNon - 1
                          END
    FROM Cuts AS C
),
Result AS
(
    SELECT
        B.*,
        OTB_Body = CASE 
                     WHEN B.OTB_Text IS NULL THEN NULL
                     ELSE LEFT(B.OTB_Text, LEN(B.OTB_Text) - ISNULL(B.OTB_TrailingLen, 0))
                   END,
        OB_Body  = CASE 
                     WHEN B.OB_Text IS NULL THEN NULL
                     ELSE LEFT(B.OB_Text,  LEN(B.OB_Text)  - ISNULL(B.OB_TrailingLen, 0))
                   END
    FROM Bodies AS B

), final as (
SELECT
    --WORKORDER_BASE_ID, WORKORDER_LOT_ID, WORKORDER_SPLIT_ID, WORKORDER_SUB_ID,
	WORKORDER_BASE_ID, 
    FULL_LOT_ID,
    WORKORDER_TYPE, SEQUENCE_NO, OPERATION_TYPE_ID
	, RESOURCE_ID,
    OTB_TrailingLen, OB_TrailingLen,
    DATALENGTH(OTB_Bits) AS OTB_Bytes, DATALENGTH(OB_Bits) AS OB_Bytes
    ,specs_Different  = case when  (OTB_Body <> OB_Body) then 1 else 0 end
    , OTB_Body, OB_Body -- uncomment to inspect textual bodies
    ,right(OTB_Body, 20) as OTB_TailText, right(OB_Body, 20) as OB_TailText

FROM Result
WHERE 1=1

--       -- Bodies are identical (to the eye, content matches)
--     AND ((OTB_Body <> OB_Body) OR (OTB_Body IS NULL AND OB_Body IS NULL))
--   AND -- Staging has more trailing CR/LF than master (this is the condition you asked to flag)
--       ISNULL(OTB_TrailingLen, 0) > ISNULL(OB_TrailingLen, 0)
	)
	select * from final
	where 1=1
	-- AND (specs_Different = @specs_Different
	--      OR @specs_Different IS NULL)
	ORDER BY -- WORKORDER_BASE_ID, SEQUENCE_NO;
    SEQUENCE_NO,
    OPERATION_TYPE_ID,
    FULL_LOT_ID
;