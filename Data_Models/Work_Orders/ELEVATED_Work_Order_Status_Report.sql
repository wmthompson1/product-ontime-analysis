/*
  PERSPECTIVE: [Production_Analytics]
  INTENT: [Schedule_Adherence]
  GOVERNANCE: [Functional Identity Mapping]
  
  DESCRIPTION:
  Elevated status report for released and firmed work orders. 
  Constructs the polymorphic WONUM (Base-Sub/Lot.Split) and 
  elevates UDF-0000035 (Material) and UDF-0000036 (Alloy) 
  from separate rows into first-class functional attributes.
*/

SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;

WITH WorkOrderBase AS (
    SELECT 
        -- Physical Identity
     --   w.ID AS work_order_id,
        w.BASE_ID,
        w.SUB_ID,
        w.LOT_ID,
        w.SPLIT_ID,
        -- Status Filter (R=Released, F=Firm, U=Unfirmed)
        w.STATUS,
        w.PART_ID,
        w.DESIRED_WANT_DATE,
        --w.ORDER_QTY,
        -- Semantic WONUM Construction (Polymorphic Root)
        (w.BASE_ID 
         + CASE WHEN ISNULL(w.SUB_ID, '0') = '0' THEN '' ELSE '-' + w.SUB_ID END
         + '/' + w.LOT_ID 
         + CASE WHEN ISNULL(w.SPLIT_ID, '0') = '0' THEN '' ELSE '.' + w.SPLIT_ID END
        ) AS WONUM
    FROM Live.dbo.WORK_ORDER w WITH (NOLOCK)
    WHERE w.TYPE = N'W' 
      AND w.STATUS IN (N'R', N'F', N'U')
),
PartUDFs AS (
    -- Elevating UDFs to First-Class Attributes
    SELECT 
        DOCUMENT_ID,
        MAX(CASE WHEN ID = N'UDF-0000035' THEN STRING_VAL END) AS [MATERIAL_SPEC],
        MAX(CASE WHEN ID = N'UDF-0000036' THEN STRING_VAL END) AS [ALLOY_SPEC]
    FROM Live.dbo.USER_DEF_FIELDS WITH (NOLOCK)
    WHERE PROGRAM_ID = N'VMPRTMNT'
      AND ID IN (N'UDF-0000035', N'UDF-0000036')
    GROUP BY DOCUMENT_ID
)
SELECT
    -- Functional Identity
    wo.WONUM,
    wo.STATUS AS [WO_STATUS],
    -- Dimensionality (Masked Mode 1)
    wo.PART_ID AS [HEX_PART_ID], 
    p.DESCRIPTION AS [PART_DESC],
    -- Elevated Attributes
    udf.MATERIAL_SPEC,
    udf.ALLOY_SPEC,
    -- Schedule Adherence Metrics
    wo.DESIRED_WANT_DATE,
    --wo.ORDER_QTY,
    p.BUYER_USER_ID,
    -- External Correlation (Buyer Assignment)
    ba.SALESPERSON_ID AS [ACCOUNT_ALIGNMENT]
FROM WorkOrderBase wo
INNER JOIN Live.dbo.PART p WITH (NOLOCK) 
    ON p.ID = wo.PART_ID
LEFT JOIN PartUDFs udf 
    ON udf.DOCUMENT_ID = wo.PART_ID
LEFT JOIN [sql-lab-2].livesupplemental.dbo.buyer_assn ba 
    ON LEFT(p.BUYER_USER_ID, 2) = ba.account_id
ORDER BY wo.DESIRED_WANT_DATE ASC;
