-- Perspective: Engineering
-- Extract specifications from binary test. 

-- An engineering master is a salection from work order where ```Work order Type` = 'M'```

/****************************report*****************************************************************
Engineer - Master Construction
William 3/4

The documentation isn't very good. The problem is that specifications were often keyboarded manually, 
and the carriage returns were not consistent. There is supposed to be two carriage returns after each line.

-- **********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results;

-- Extract a list of all parts where using Operation_Type for initialization

-- Perspective: Engineering
-- ** Base As Part: ** 
-- pespective ignores this
DECLARE @WorkorderBaseId   varchar(50)  = NULL -- '1801017'; ---1803245'; --'313Z7430-504'   -- '5000-6619-001' --  '635TEST-LOS-EME-ALBRKTP';      -- e.g., '5000-6730-001'
DECLARE @SPLIT_ID NVARCHAR(3) = NULL;;
DECLARE @WorkorderType     char(1)      = 'm';      -- e.g., 'M'
DECLARE @TEST INT       = 0;        
DECLARE @TEST1 INT       = 0; 

-- pespective ignores this
DECLARE @OPTYPE NVARCHAR(MAX) = 'F20.03'; 
declare @specs_Different BIT = null;

;WITH J AS
(
    SELECT  top 100000
        -- Keys (adjust if needed)
        o.WORKORDER_BASE_ID
        ,ot.description as OPERATION_TYPE_Description
        ,o.WORKORDER_split_ID 
        , o.WORKORDER_LOT_ID
        ,o.WORKORDER_SUB_ID

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


    WHERE 1=1
     AND (o.OPERATION_TYPE IN (@OPTYPE) OR @OPTYPE IS NULL) -- filter to specific operation type(s) if needed
	AND (o.WORKORDER_BASE_ID in ( @WorkorderBaseId) OR @WorkorderBaseId IS NULL)
    AND (o.WORKORDER_SPLIT_ID = @SPLIT_ID OR @SPLIT_ID IS NULL)
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
        ,
                -- Normalize line endings to LF only for reliable paragraph detection
                OTB_Text_N = CASE WHEN C.OTB_Text IS NULL THEN NULL ELSE REPLACE(REPLACE(C.OTB_Text, CHAR(13) + CHAR(10), CHAR(10)), CHAR(13), CHAR(10)) END,
                OB_Text_N  = CASE WHEN C.OB_Text  IS NULL THEN NULL ELSE REPLACE(REPLACE(C.OB_Text,  CHAR(13) + CHAR(10), CHAR(10)), CHAR(13), CHAR(10)) END,
                -- Clean up whitespace-only blank lines and collapse many LFs into exactly two LF paragraph separators
                OTB_Text_Clean = CASE WHEN C.OTB_Text IS NULL THEN NULL ELSE
                        REPLACE(
                            REPLACE(
                                REPLACE(
                                    REPLACE(
                                        REPLACE(REPLACE(C.OTB_Text, CHAR(13) + CHAR(10), CHAR(10)), CHAR(13), CHAR(10)),
                                    CHAR(9), ''), -- remove tabs
                                CHAR(10) + ' ' + CHAR(10), CHAR(10) + CHAR(10)),
                            CHAR(10) + '  ' + CHAR(10), CHAR(10) + CHAR(10)),
                        CHAR(10) + '   ' + CHAR(10), CHAR(10) + CHAR(10))
                        END,
                OB_Text_Clean = CASE WHEN C.OB_Text IS NULL THEN NULL ELSE
                        REPLACE(
                            REPLACE(
                                REPLACE(
                                    REPLACE(
                                        REPLACE(REPLACE(C.OB_Text, CHAR(13) + CHAR(10), CHAR(10)), CHAR(13), CHAR(10)),
                                    CHAR(9), ''),
                                CHAR(10) + ' ' + CHAR(10), CHAR(10) + CHAR(10)),
                            CHAR(10) + '  ' + CHAR(10), CHAR(10) + CHAR(10)),
                        CHAR(10) + '   ' + CHAR(10), CHAR(10) + CHAR(10))
                        END
    FROM Cuts AS C
),
Paragraph2 AS
(
    SELECT
        B.*,
        -- Debugging originals
        OTB_Text_Debug = B.OTB_Text,
        OB_Text_Debug  = B.OB_Text,

           -- locate double-LF in cleaned text
           OTB_FirstLF = NULLIF(CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean), 0),
           OTB_SecondLF = NULLIF(CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) + 2), 0),
           OB_FirstLF = NULLIF(CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean), 0),
           OB_SecondLF = NULLIF(CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) + 2), 0),

                     OTB_Paragraph2 = CASE
                            WHEN B.OTB_Text_Clean IS NULL THEN NULL
                            WHEN CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) = 0 THEN NULL
                            ELSE SUBSTRING(
                                        B.OTB_Text_Clean,
                                        CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) + 2,
                                        CASE WHEN CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) + 2) = 0
                                                 THEN LEN(B.OTB_Text_Clean) - CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) - 1
                                                 ELSE CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) + 2) - CHARINDEX(CHAR(10) + CHAR(10), B.OTB_Text_Clean) - 2
                                        END
                                    )
                     END,

                     OB_Paragraph2 = CASE
                            WHEN B.OB_Text_Clean IS NULL THEN NULL
                            WHEN CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) = 0 THEN NULL
                            ELSE SUBSTRING(
                                        B.OB_Text_Clean,
                                        CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) + 2,
                                        CASE WHEN CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) + 2) = 0
                                                 THEN LEN(B.OB_Text_Clean) - CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) - 1
                                                 ELSE CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) + 2) - CHARINDEX(CHAR(10) + CHAR(10), B.OB_Text_Clean) - 2
                                        END
                                    )
                     END,

                     -- Extract second physical line (single LF-separated) from cleaned text
                     OTB_Line_FirstLF = NULLIF(CHARINDEX(CHAR(10), B.OTB_Text_Clean),0),
                     OTB_Line_SecondLF = NULLIF(CHARINDEX(CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10), B.OTB_Text_Clean) + 1),0),
                     OTB_Line2 = CASE
                            WHEN B.OTB_Text_Clean IS NULL THEN NULL
                            WHEN CHARINDEX(CHAR(10), B.OTB_Text_Clean) = 0 THEN NULL
                            ELSE SUBSTRING(
                                        B.OTB_Text_Clean,
                                        CHARINDEX(CHAR(10), B.OTB_Text_Clean) + 1,
                                        CASE WHEN CHARINDEX(CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10), B.OTB_Text_Clean) + 1) = 0
                                                 THEN LEN(B.OTB_Text_Clean) - CHARINDEX(CHAR(10), B.OTB_Text_Clean)
                                                 ELSE CHARINDEX(CHAR(10), B.OTB_Text_Clean, CHARINDEX(CHAR(10), B.OTB_Text_Clean) + 1) - CHARINDEX(CHAR(10), B.OTB_Text_Clean) - 1
                                        END
                                    )
                     END,
                     OB_Line_FirstLF = NULLIF(CHARINDEX(CHAR(10), B.OB_Text_Clean),0),
                     OB_Line_SecondLF = NULLIF(CHARINDEX(CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10), B.OB_Text_Clean) + 1),0),
                     OB_Line2 = CASE
                            WHEN B.OB_Text_Clean IS NULL THEN NULL
                            WHEN CHARINDEX(CHAR(10), B.OB_Text_Clean) = 0 THEN NULL
                            ELSE SUBSTRING(
                                        B.OB_Text_Clean,
                                        CHARINDEX(CHAR(10), B.OB_Text_Clean) + 1,
                                        CASE WHEN CHARINDEX(CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10), B.OB_Text_Clean) + 1) = 0
                                                 THEN LEN(B.OB_Text_Clean) - CHARINDEX(CHAR(10), B.OB_Text_Clean)
                                                 ELSE CHARINDEX(CHAR(10), B.OB_Text_Clean, CHARINDEX(CHAR(10), B.OB_Text_Clean) + 1) - CHARINDEX(CHAR(10), B.OB_Text_Clean) - 1
                                        END
                                    )
                     END
    FROM Bodies AS B
),
Result AS
(
                SELECT
                        B.*,
                        -- Use cleaned LF-normalized text as the body (avoids referencing OTB_Text_N/OB_Text_N)
                        OTB_Body = B.OTB_Text_Clean,
                        OB_Body  = B.OB_Text_Clean
                FROM Paragraph2 AS B

    ), final as (
    SELECT
        WORKORDER_BASE_ID, 
        OPERATION_TYPE_Description,
        FULL_LOT_ID,
        WORKORDER_TYPE, SEQUENCE_NO, OPERATION_TYPE_ID,
        RESOURCE_ID,
        OTB_Paragraph2, OB_Paragraph2,
        OTB_Line2, OB_Line2,
        OTB_TrailingLen, OB_TrailingLen,
        DATALENGTH(OTB_Bits) AS OTB_Bytes, DATALENGTH(OB_Bits) AS OB_Bytes,
       ---- specs_Different  = case when  (OTB_Body <> OB_Body) then 1 else 0 end,
        OTB_Body, OB_Body,
        right(OTB_Body, 20) as OTB_TailText, right(OB_Body, 20) as OB_TailText

    FROM Result
    WHERE 1=1

    )
    select * from final
    where 1=1
    and operation_type_id = 'F20.03' -- filter to specific operation type if needed
    ORDER BY
    SEQUENCE_NO,
    OPERATION_TYPE_ID,
    OPERATION_TYPE_Description,
    FULL_LOT_ID
    ;
;