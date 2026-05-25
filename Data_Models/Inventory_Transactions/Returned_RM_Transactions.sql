/*
  Returned_RM_Transactions.sql

  Purpose: Find inventory transactions related to returned raw materials for
  requirements with STATUS = 'R'. Includes trace/lot/serial detail and attempts
  to surface paired transactions (Issue Return / Receipt Return) when available.

  Usage:
    - Set date window and optional filters below before running.
    - Example: set @StartDate = '2025-11-01'; @EndDate = GETDATE();

  Notes:
    - Transaction TYPE/CLASS codes: See authoritative reference at
      Documentation/Data Models/Inventory_Transactions/Inventory_Transaction_Terminology_Guide.md
      * Issue Return: CLASS='I', TYPE='I' (WO → Inventory, +QTY)
      * Scenario	Class	Type	Class Tag	Type Tag	Effect on QOH	Database Query Pattern
      * 5	I	I	Issue	In	+1 * QTY	TYPE = 'I' AND CLASS = 'I'
    - To limit to specific transaction types, add filters to the WHERE clause near
      the bottom (comments indicate where).
      - This query uses `TRACE_INV_TRANS` for trace linkage and `TRACE` for
        lot/serial fields. Adjust field names if your trace table uses different
        column names.
      - Note: the physical "lot" detail in this installation is stored in the
        flex field `TRACE.APROPERTY_1`. See `Documentation/Data Models/Inventory_Transactions/trace_lot_mapping.md`
        for mapping details and examples. The `Trace_AProperty_1` column is
        selected below to surface that value alongside `LOT_ID`.
*/

SET NOCOUNT ON;

-- Parameters: change as needed
DECLARE @StartDate  DATETIME = DATEADD(month,-3,GETDATE()); -- default: last 3 months
DECLARE @EndDate    DATETIME = GETDATE();
DECLARE @PartID     NVARCHAR(30) = NULL;    -- optional: filter to a single part
DECLARE @WorkOrder  NVARCHAR(30) = NULL;    -- optional: filter to a single work order base id
DECLARE @TopN       INT = NULL;             -- optional: limit rows

-- CTE for requirements that are Released
;WITH CTE_Req AS (
    SELECT r.*
    FROM REQUIREMENT r WITH (NOLOCK)
    WHERE r.STATUS = 'R'
),

-- Inventory transactions with trace info
CTE_Inv AS (
    SELECT
        it.TRANSACTION_ID,
        it.PART_ID,
        it.TYPE,
        it.CLASS,
        it.QTY,
        it.COSTED_QTY,
        it.TRANSACTION_DATE,
        it.WAREHOUSE_ID,
        it.LOCATION_ID,
     --   it.DESCRIPTION,
        it.WORKORDER_TYPE,
        it.WORKORDER_BASE_ID,
        it.WORKORDER_LOT_ID,
        it.WORKORDER_SPLIT_ID,
        it.WORKORDER_SUB_ID,
        tit.TRACE_ID
    FROM INVENTORY_TRANS it WITH (NOLOCK)
    LEFT JOIN TRACE_INV_TRANS tit WITH (NOLOCK)
        ON tit.TRANSACTION_ID = it.TRANSACTION_ID
    WHERE it.TRANSACTION_DATE BETWEEN @StartDate AND @EndDate
),

-- Dist records that may link paired transactions (IN/OUT)
CTE_Dist AS (
    SELECT *
    FROM INV_TRANS_DIST WITH (NOLOCK)
)

SELECT
    r.WORKORDER_TYPE            AS Requirement_WO_Type,
    r.WORKORDER_BASE_ID         AS Requirement_WO_Base_ID,
    r.WORKORDER_LOT_ID          AS Requirement_WO_Lot_ID,
    r.WORKORDER_SPLIT_ID        AS Requirement_WO_Split_ID,
    r.PART_ID                   AS Requirement_Part_ID,
    r.OPERATION_SEQ_NO          AS Requirement_Op_Seq,
    r.PIECE_NO                  AS Requirement_Piece_No,
    r.CALC_QTY                  AS Requirement_Required_Qty,

    it.TRANSACTION_ID,
    it.PART_ID                  AS Trans_Part_ID,
    it.TYPE                     AS Trans_Type,
    it.CLASS                    AS Trans_Class,
    it.QTY                      AS Trans_Qty,
    it.TRANSACTION_DATE         AS Trans_Date,
    it.WAREHOUSE_ID,
    it.LOCATION_ID,
 --   it.DESCRIPTION,
    it.WORKORDER_BASE_ID        AS Trans_WO_Base_ID,
    it.WORKORDER_LOT_ID         AS Trans_WO_Lot_ID,
    it.WORKORDER_SPLIT_ID       AS Trans_WO_Split_ID,
    it.WORKORDER_SUB_ID         AS Trans_WO_Sub_ID,

    it.TRACE_ID,
    -- tr.LOT_ID                   AS Trace_Lot_ID,
    -- tr.SERIAL_ID                AS Trace_Serial_ID,
    tr.APROPERTY_1              AS Trace_Lot_ID,

    -- paired transaction if linked via INV_TRANS_DIST
    paired.TRANSACTION_ID       AS Paired_Transaction_ID,
    paired.TYPE                 AS Paired_Type,
    paired.CLASS                AS Paired_Class,
    paired.QTY                  AS Paired_Qty,
    paired.TRANSACTION_DATE     AS Paired_Trans_Date,
    paired.WAREHOUSE_ID         AS Paired_Warehouse_ID,
    paired.LOCATION_ID          AS Paired_Location_ID

FROM CTE_Req r
INNER JOIN CTE_Inv it
    ON r.WORKORDER_BASE_ID = it.WORKORDER_BASE_ID
    AND ISNULL(r.WORKORDER_LOT_ID,'') = ISNULL(it.WORKORDER_LOT_ID,'')
    AND ISNULL(r.WORKORDER_SPLIT_ID,'') = ISNULL(it.WORKORDER_SPLIT_ID,'')
    AND ISNULL(r.WORKORDER_SUB_ID,0) = ISNULL(it.WORKORDER_SUB_ID,0)
    AND r.PART_ID = it.PART_ID

-- try to find a linked IN/OUT transaction via INV_TRANS_DIST
LEFT JOIN CTE_Dist d
    ON d.IN_TRANS_ID = it.TRANSACTION_ID OR d.OUT_TRANS_ID = it.TRANSACTION_ID

LEFT JOIN INVENTORY_TRANS paired WITH (NOLOCK)
    ON (paired.TRANSACTION_ID = d.OUT_TRANS_ID AND paired.TRANSACTION_ID <> it.TRANSACTION_ID)
    OR (paired.TRANSACTION_ID = d.IN_TRANS_ID AND paired.TRANSACTION_ID <> it.TRANSACTION_ID)

-- join to TRACE table to get lot/serial fields (TRACE.ID = TRACE_INV_TRANS.TRACE_ID)
LEFT JOIN TRACE tr WITH (NOLOCK)
  ON tr.ID = it.TRACE_ID

WHERE 1=1
   and it.WAREHOUSE_ID = 'Auburn Mtl Cage'
      -- Scenario	Class	Type	Class Tag	Type Tag	Effect on QOH	Database Query Pattern
      -- * 5	I	I	Issue	In	+1 * QTY	TYPE = 'I' AND CLASS = 'I'
  AND it.TYPE = 'I'
  AND it.CLASS = 'I'

  -- optional filters
  AND (@PartID IS NULL OR it.PART_ID = @PartID)
  AND (@WorkOrder IS NULL OR it.WORKORDER_BASE_ID = @WorkOrder)

ORDER BY it.TRANSACTION_DATE DESC
