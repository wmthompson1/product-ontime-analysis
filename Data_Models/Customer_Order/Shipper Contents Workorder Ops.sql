

declare @PACKLIST_ID nvarchar(50) = '1447859';  -- -- 1447859
declare @TOPPER int = 1; --1000000

/**********************************************************************************************
Description:
Sample:
Date      Modified By      Change Description
---------- ------------------ ------------------------------------------------------------
**********************************************************************************************/
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW
IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results

-- wpould you create a create table for #tmpShipper and use the correct table ddl to create the table and insert the data into it.
IF OBJECT_ID('tempdb..#ShipperContents') IS NOT NULL DROP TABLE #ShipperContents
CREATE TABLE #ShipperContents (
    PACKLIST_ID NVARCHAR(15) NOT NULL,
    SUPPLY_BASE_ID NVARCHAR(30) NOT NULL,
    SUPPLY_LOT_ID NVARCHAR(15) NULL,
    SUPPLY_SUB_ID NVARCHAR(3) NULL,
    SUPPLY_SPLIT_ID NVARCHAR(3) NULL,
    TRANSACTION_ID INT NULL,
    TRACE_ID NVARCHAR(30) NULL,
    PART_ID NVARCHAR(30) NULL,
    USER_1 NVARCHAR(80) NULL,
    USER_2 NVARCHAR(80) NULL,
    USER_3 NVARCHAR(80) NULL,
    USER_4 NVARCHAR(80) NULL,
    USER_5 NVARCHAR(80) NULL,
    USER_6 NVARCHAR(80) NULL,
    USER_7 NVARCHAR(80) NULL,
    USER_8 NVARCHAR(80) NULL,
    USER_9 NVARCHAR(80) NULL,
    USER_10 NVARCHAR(80) NULL,
    CUST_ORDER_ID NVARCHAR(15) NOT NULL,
    CUST_ORDER_LINE_NO SMALLINT NULL,
    CUSTOMER_PART_ID NVARCHAR(30) NULL,
    CUSTOMER_PO_REF NVARCHAR(40) NULL,
    CUSTOMER_ID NVARCHAR(15) NOT NULL,
    SHIP_TO_ADDR_NO INT NULL,
    CUST_POLN_PRINT NCHAR(1) NOT NULL,
    CUST_PO_LN NVARCHAR(80) NULL,
    WO_SHIPPED_QTY DECIMAL(20,8) NOT NULL
)

INSERT INTO #ShipperContents (
    PACKLIST_ID,
    SUPPLY_BASE_ID,
    SUPPLY_LOT_ID,
    SUPPLY_SUB_ID,
    SUPPLY_SPLIT_ID,
    TRANSACTION_ID,
    TRACE_ID,
    PART_ID,
    USER_1,
    USER_2,
    USER_3,
    USER_4,
    USER_5,
    USER_6,
    USER_7,
    USER_8,
    USER_9,
    USER_10,
    CUST_ORDER_ID,
    CUST_ORDER_LINE_NO,
    CUSTOMER_PART_ID,
    CUSTOMER_PO_REF,
    CUSTOMER_ID,
    SHIP_TO_ADDR_NO,
    CUST_POLN_PRINT,
    CUST_PO_LN,
    WO_SHIPPED_QTY
)
SELECT TOP (@TOPPER)
    SL.PACKLIST_ID,
    DSL.SUPPLY_BASE_ID,
    DSL.SUPPLY_LOT_ID,
    DSL.SUPPLY_SUB_ID,
    DSL.SUPPLY_SPLIT_ID,
    TRT.TRANSACTION_ID,
    TRT.TRACE_ID,
    COL.PART_ID,
    S.USER_1,
    S.USER_2,
    S.USER_3,
    S.USER_4,
    S.USER_5,
    S.USER_6,
    S.USER_7,
    S.USER_8,
    S.USER_9,
    S.USER_10,
    SL.CUST_ORDER_ID,
    SL.CUST_ORDER_LINE_NO,
    COL.CUSTOMER_PART_ID,
    CO.CUSTOMER_PO_REF,
    CO.CUSTOMER_ID,
    CO.SHIP_TO_ADDR_NO,
    CASE WHEN COL.USER_2 IS NOT NULL THEN 'Y' ELSE 'N' END AS CUST_POLN_PRINT,
    COL.USER_2 AS CUST_PO_LN,
    ISNULL(ABS(TRT.QTY), SL.SHIPPED_QTY) AS WO_SHIPPED_QTY
FROM SHIPPER_LINE SL
JOIN CUST_ORDER_LINE COL
    ON SL.CUST_ORDER_ID = COL.CUST_ORDER_ID
    AND SL.CUST_ORDER_LINE_NO = COL.LINE_NO
LEFT JOIN DEMAND_SUPPLY_LINK DSL
    ON COL.CUST_ORDER_ID = DSL.DEMAND_BASE_ID
    AND COL.LINE_NO = DSL.DEMAND_SEQ_NO
JOIN CUSTOMER_ORDER CO
    ON COL.CUST_ORDER_ID = CO.ID
LEFT JOIN TRACE_INV_TRANS TRT
    ON TRT.TRANSACTION_ID = SL.TRANSACTION_ID
JOIN SHIPPER S
    ON SL.PACKLIST_ID = S.PACKLIST_ID
WHERE (SL.PACKLIST_ID = @PACKLIST_ID OR @PACKLIST_ID IS NULL)
    AND ISNULL(ABS(TRT.QTY), SL.SHIPPED_QTY) > 0
    ;

-- test
--SELECT * FROM #ShipperContents;

WITH ShipperContents AS (
    Select 1 as col

-- SELECT TOP (@TOPPER)      DSL.SUPPLY_BASE_ID, DSL.SUPPLY_LOT_ID, DSL.SUPPLY_SUB_ID, DSL.SUPPLY_SPLIT_ID
-- 					, TRT.TRANSACTION_ID, TRT.TRACE_ID, COL.PART_ID, S.USER_1, S.USER_2, S.USER_3, S.USER_4, 
--                     S.USER_5, S.USER_6, S.USER_7, S.USER_8, S.USER_9, S.USER_10, SL.CUST_ORDER_ID, SL.CUST_ORDER_LINE_NO
-- 					, COL.CUSTOMER_PART_ID  /*line 20*/ 
-- 					, CO.CUSTOMER_PO_REF, 
--                     CO.CUSTOMER_ID, CO.SHIP_TO_ADDR_NO, CASE WHEN COL.USER_2 IS NOT NULL THEN 'Y' ELSE 'N' END AS CUST_POLN_PRINT
-- 								, COL.USER_2 AS CUST_PO_LN, ISNULL(ABS(TRT.QTY), 
--                                 SL.SHIPPED_QTY) AS WO_SHIPPED_QTY
--         /*col26*/ 
-- 		FROM SHIPPER_LINE SL JOIN
--                                 CUST_ORDER_LINE COL ON SL.CUST_ORDER_ID = COL.CUST_ORDER_ID AND SL.CUST_ORDER_LINE_NO = COL.LINE_NO LEFT JOIN
--                                 DEMAND_SUPPLY_LINK DSL ON COL.CUST_ORDER_ID = DSL.DEMAND_BASE_ID AND COL.LINE_NO = DSL.DEMAND_SEQ_NO JOIN
--                                 CUSTOMER_ORDER CO ON COL.CUST_ORDER_ID = CO.ID LEFT JOIN
--                                 TRACE_INV_TRANS TRT ON TRT.TRANSACTION_ID = SL.TRANSACTION_ID JOIN
--                                 SHIPPER S ON SL.PACKLIST_ID = S.PACKLIST_ID
--         WHERE        (SL.PACKLIST_ID = @PACKLIST_ID OR @PACKLIST_ID IS NULL)
-- 		AND ISNULL(ABS(TRT.QTY), SL.SHIPPED_QTY) > 0
        
        )
, OPERATIONS AS
    (SELECT        *
      FROM            OPERATION
      WHERE        WORKORDER_BASE_ID IN
                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/', REPLACE(TRACE_ID, '.', '/')) - 1))
                                      FROM            #ShipperContents))
, WORKORDERS AS
    (SELECT        *
      FROM            WORK_ORDER
      WHERE        BASE_ID IN
                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/', REPLACE(TRACE_ID, '.', '/')) - 1))
                                      FROM            #ShipperContents) AND TYPE = 'W')
, WORKORDER_COPRODUCTS AS
    (SELECT        C.PART_ID, ISNULL(sc.WO_SHIPPED_QTY, C.DESIRED_QTY) AS ShippedQTY, sc.CUST_ORDER_ID, sc.CUST_ORDER_LINE_NO, sc.CUSTOMER_PART_ID, 
                                sc.CUSTOMER_PO_REF
								
								/*,C.WORKORDER_BASE_ID + '/' + C.WORKORDER_LOT_ID + '/' + C.WORKORDER_SPLIT_ID +'/' + C.WORKORDER_SUB_ID */ 
								
								, dbo.sfnWONUMFormat(C.WORKORDER_BASE_ID, 
                                C.WORKORDER_LOT_ID, C.WORKORDER_SPLIT_ID, C.WORKORDER_SUB_ID) AS CURRENT_WO_ID, dbo.sfnWONUMFormat_OLD(C.WORKORDER_BASE_ID, C.WORKORDER_LOT_ID, C.WORKORDER_SPLIT_ID, 
                                C.WORKORDER_SUB_ID) AS OLD_WO_ID, sc.CUSTOMER_ID
      FROM            CO_PRODUCT C 
	  LEFT JOIN
                                #ShipperContents sc ON sc.SUPPLY_BASE_ID = C.WORKORDER_BASE_ID AND sc.SUPPLY_LOT_ID = C.WORKORDER_LOT_ID AND sc.SUPPLY_SUB_ID = C.WORKORDER_SUB_ID AND 
                                sc.SUPPLY_SPLIT_ID = C.WORKORDER_SPLIT_ID AND c.WORKORDER_TYPE = 'W' AND c.PART_ID = sc.PART_ID
      WHERE        EXISTS
                                    (SELECT        1
                                      FROM            WORKORDERS W JOIN
                                                                #ShipperContents S ON W.BASE_ID IN
                                                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/', REPLACE(TRACE_ID, '.', '/')) - 1)))
                                      WHERE        C.WORKORDER_BASE_ID = W.BASE_ID AND C.WORKORDER_LOT_ID = W.LOT_ID
									  AND C.WORKORDER_SUB_ID = W.SUB_ID AND C.WORKORDER_SPLIT_ID = W.SPLIT_ID))
----, WORKORDER_OPS_BREAKDOWN AS
----    (/*GET SPLITS -LINKED AND UNLINKED*/ 
	-- ~22
				SELECT 
                   sc.PACKLIST_ID AS PACKLIST_ID,
                   sc.SUPPLY_BASE_ID, sc.SUPPLY_LOT_ID, sc.SUPPLY_SUB_ID, sc.SUPPLY_SPLIT_ID,
                   sc.TRANSACTION_ID, sc.TRACE_ID, sc.PART_ID, sc.USER_1, sc.USER_2, sc.USER_3, sc.USER_4,
                   sc.USER_5, sc.USER_6, sc.USER_7, sc.USER_8, sc.USER_9, sc.USER_10, sc.CUST_ORDER_ID, sc.CUST_ORDER_LINE_NO,
                   sc.CUSTOMER_PART_ID, sc.CUSTOMER_PO_REF, sc.CUSTOMER_ID, sc.SHIP_TO_ADDR_NO, sc.CUST_POLN_PRINT,
                   sc.CUST_PO_LN, sc.WO_SHIPPED_QTY, x.StepsFromChild, x.SequenceNo, x.BASE_ID, x.LOT_ID, x.SUB_ID
							   , x.SPLIT_ID AS SourceWO_SPLIT_ID/*col32*/ , ISNULL(WO.SPLIT_ID, WO2.SPLIT_ID) AS CURRENT_SPLIT_ID, 
											x.OPERATION_TYPE, x.RESOURCE_ID, x.SERVICE_ID
								
											/*, x.BASE_ID +'/'+ x.LOT_ID +'/'+ WO.SPLIT_ID+'/'+ x.SUB_ID */ 
								
											, ISNULL(sc.TRACE_ID, dbo.sfnWONUMFormat(x.BASE_ID, x.LOT_ID, WO.SPLIT_ID, x.SUB_ID)) 
											AS CURRENT_WO_ID
								
											/*, dbo.sfnWONUMFormat_OLD (x.BASE_ID, x.LOT_ID, WO.SPLIT_ID, x.SUB_ID ) AS OLD_WO_ID*/ 

											, 'main product' AS PartSource, CASE WHEN SUPPLY_BASE_ID IS NULL 
											THEN 'unlinked order' ELSE 'linked order' END AS FulfillmentMethod
				  FROM            #ShipperContents sc 
				  LEFT JOIN
								   WORKORDERS WO ON sc.TRACE_ID = dbo.sfnWONUMFormat(WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID) 
										AND sc.SUPPLY_BASE_ID IS NULL AND WO.COPY_FROM_SPLIT_ID IS NOT NULL AND 
											WO.PART_ID = sc.PART_ID 
								
											/*ADDED TO PREVENT RETURN OF CO-PRODUCTS*/ 
								
				  LEFT JOIN
								   WORKORDERS WO2 ON sc.TRACE_ID = dbo.sfnWONUMFormat_OLD(WO2.BASE_ID, WO2.LOT_ID, WO2.SPLIT_ID, WO2.SUB_ID) 
										AND sc.SUPPLY_BASE_ID IS NULL AND WO2.COPY_FROM_SPLIT_ID IS NOT NULL AND 
											WO2.PART_ID = sc.PART_ID 
								
											/*ADDED TO PREVENT RETURN OF CO-PRODUCTS*/ 

				  CROSS APPLY dbo.sfnGetSplitParentOperations(COALESCE (SUPPLY_BASE_ID, WO.BASE_ID, WO2.BASE_ID), COALESCE (SUPPLY_LOT_ID,
											 WO.LOT_ID, WO2.LOT_ID), COALESCE (SUPPLY_SUB_ID, WO.SUB_ID, WO2.SUB_ID), COALESCE (SUPPLY_SPLIT_ID, WO.SPLIT_ID, WO2.SPLIT_ID)) x
		UNION ALL  --~22
				  /*GET NON-SPLITS Unlinked Orders*/ 
				  -- ~22
				 SELECT 
                     sc.PACKLIST_ID AS PACKLIST_ID,
                     sc.SUPPLY_BASE_ID, sc.SUPPLY_LOT_ID, sc.SUPPLY_SUB_ID, sc.SUPPLY_SPLIT_ID,
                     sc.TRANSACTION_ID, sc.TRACE_ID, sc.PART_ID, sc.USER_1, sc.USER_2, sc.USER_3, sc.USER_4,
                     sc.USER_5, sc.USER_6, sc.USER_7, sc.USER_8, sc.USER_9, sc.USER_10, sc.CUST_ORDER_ID, sc.CUST_ORDER_LINE_NO,
                     sc.CUSTOMER_PART_ID, sc.CUSTOMER_PO_REF, sc.CUSTOMER_ID, sc.SHIP_TO_ADDR_NO, sc.CUST_POLN_PRINT,
                     sc.CUST_PO_LN, sc.WO_SHIPPED_QTY, 0, O.SEQUENCE_NO, WO.BASE_ID, WO.LOT_ID, WO.SUB_ID, WO.SPLIT_ID, WO.SPLIT_ID, O.OPERATION_TYPE, O.RESOURCE_ID, O.SERVICE_ID, ISNULL(sc.TRACE_ID, 
										   dbo.sfnWONUMFormat(WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID))
						/*, dbo.sfnWONUMFormat_OLD (WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID) */ 
						, 'main product' AS PartSource, 'unlinked order'
				  FROM            #ShipperContents sc JOIN
										   WORKORDERS WO ON (sc.TRACE_ID = dbo.sfnWONUMFormat(WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID) OR
										   sc.TRACE_ID = dbo.sfnWONUMFormat_OLD(WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID))
										   /*AND sc.SUPPLY_BASE_ID IS NULL*/ AND WO.COPY_FROM_SPLIT_ID IS NULL AND WO.SPLIT_ID = '0' AND 
										   WO.PART_ID = sc.PART_ID 
										   /*ADDED TO PREVENT RETURN OF CO-PRODUCTS*/ 
										   JOIN
										   OPERATIONS O ON WO.BASE_ID = O.WORKORDER_BASE_ID AND WO.LOT_ID = O.WORKORDER_LOT_ID 
										   AND WO.SUB_ID = O.WORKORDER_SUB_ID AND WO.SPLIT_ID = O.WORKORDER_SPLIT_ID AND 
										   O.WORKORDER_TYPE = 'W'
		UNION ALL -- ~22

				  /*GET NON-SPLITS Linked Orders*/ 
				  -- ~22
				  SELECT 
                    sc.PACKLIST_ID AS PACKLIST_ID,
                    sc.SUPPLY_BASE_ID, sc.SUPPLY_LOT_ID, sc.SUPPLY_SUB_ID, sc.SUPPLY_SPLIT_ID,
                    sc.TRANSACTION_ID, sc.TRACE_ID, sc.PART_ID, sc.USER_1, sc.USER_2, sc.USER_3, sc.USER_4,
                    sc.USER_5, sc.USER_6, sc.USER_7, sc.USER_8, sc.USER_9, sc.USER_10, sc.CUST_ORDER_ID, sc.CUST_ORDER_LINE_NO,
                    sc.CUSTOMER_PART_ID, sc.CUSTOMER_PO_REF, sc.CUSTOMER_ID, sc.SHIP_TO_ADDR_NO, sc.CUST_POLN_PRINT,
                    sc.CUST_PO_LN, sc.WO_SHIPPED_QTY, 0, O.SEQUENCE_NO, WO.BASE_ID, WO.LOT_ID, WO.SUB_ID, WO.SPLIT_ID, WO.SPLIT_ID, O.OPERATION_TYPE, O.RESOURCE_ID
					, O.SERVICE_ID, dbo.sfnWONUMFormat(WO.BASE_ID, 
										   WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID)
										   /*, dbo.sfnWONUMFormat_OLD (WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID)*/ 
										   , 'main product' AS PartSource, 'linked order'
				  FROM            #ShipperContents sc JOIN
										   WORKORDERS WO ON sc.SUPPLY_BASE_ID = WO.BASE_ID AND sc.SUPPLY_LOT_ID = WO.LOT_ID 
										   AND sc.SUPPLY_SUB_ID = WO.SUB_ID AND sc.SUPPLY_SPLIT_ID = WO.SPLIT_ID AND 
										   WO.COPY_FROM_SPLIT_ID IS NULL AND WO.PART_ID = sc.PART_ID 
										   /*ADDED TO PREVENT RETURN OF CO-PRODUCTS*/ 
										   JOIN
										   OPERATIONS O ON WO.BASE_ID = O.WORKORDER_BASE_ID AND WO.LOT_ID = O.WORKORDER_LOT_ID
										   AND WO.SUB_ID = O.WORKORDER_SUB_ID AND WO.SPLIT_ID = O.WORKORDER_SPLIT_ID AND 
										   WO.TYPE = O.WORKORDER_TYPE