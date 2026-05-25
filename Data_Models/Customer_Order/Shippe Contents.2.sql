-- test

-- dependencies: sfnGetSplitParentOperations, sfnSKILLS_WO_DOC_LINK_NO_LOC, sfnWONUMFormat, sfnWONUMFormat

declare @PACKLIST_ID nvarchar(50) = NULL;
declare @TOPPER int = 1; --1000000

WITH ShipperContents AS (

SELECT TOP (@TOPPER)      DSL.SUPPLY_BASE_ID, DSL.SUPPLY_LOT_ID, DSL.SUPPLY_SUB_ID, DSL.SUPPLY_SPLIT_ID
					, TRT.TRANSACTION_ID, TRT.TRACE_ID, COL.PART_ID, S.USER_1, S.USER_2, S.USER_3, S.USER_4, 
                    S.USER_5, S.USER_6, S.USER_7, S.USER_8, S.USER_9, S.USER_10, SL.CUST_ORDER_ID, SL.CUST_ORDER_LINE_NO
					, COL.CUSTOMER_PART_ID  /*line 20*/ 
					, CO.CUSTOMER_PO_REF, 
                    CO.CUSTOMER_ID, CO.SHIP_TO_ADDR_NO, CASE WHEN COL.USER_2 IS NOT NULL THEN 'Y' ELSE 'N' END AS CUST_POLN_PRINT
								, COL.USER_2 AS CUST_PO_LN, ISNULL(ABS(TRT.QTY), 
                                SL.SHIPPED_QTY) AS WO_SHIPPED_QTY
        /*col26*/ 
		FROM SHIPPER_LINE SL JOIN
                                CUST_ORDER_LINE COL ON SL.CUST_ORDER_ID = COL.CUST_ORDER_ID AND SL.CUST_ORDER_LINE_NO = COL.LINE_NO LEFT JOIN
                                DEMAND_SUPPLY_LINK DSL ON COL.CUST_ORDER_ID = DSL.DEMAND_BASE_ID AND COL.LINE_NO = DSL.DEMAND_SEQ_NO JOIN
                                CUSTOMER_ORDER CO ON COL.CUST_ORDER_ID = CO.ID LEFT JOIN
                                TRACE_INV_TRANS TRT ON TRT.TRANSACTION_ID = SL.TRANSACTION_ID JOIN
                                SHIPPER S ON SL.PACKLIST_ID = S.PACKLIST_ID
        WHERE        (SL.PACKLIST_ID = @PACKLIST_ID OR @PACKLIST_ID IS NULL)
		AND ISNULL(ABS(TRT.QTY), SL.SHIPPED_QTY) > 0)
, OPERATIONS AS
    (SELECT        *
      FROM            OPERATION
      WHERE        WORKORDER_BASE_ID IN
                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/', REPLACE(TRACE_ID, '.', '/')) - 1))
                                      FROM            ShipperContents))
, WORKORDERS AS
    (SELECT        *
      FROM            WORK_ORDER
      WHERE        BASE_ID IN
                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/', REPLACE(TRACE_ID, '.', '/')) - 1))
                                      FROM            ShipperContents) AND TYPE = 'W')
, WORKORDER_COPRODUCTS AS
    (SELECT        C.PART_ID, ISNULL(sc.WO_SHIPPED_QTY, C.DESIRED_QTY) AS ShippedQTY, sc.CUST_ORDER_ID, sc.CUST_ORDER_LINE_NO, sc.CUSTOMER_PART_ID, 
                                sc.CUSTOMER_PO_REF
								
								/*,C.WORKORDER_BASE_ID + '/' + C.WORKORDER_LOT_ID + '/' + C.WORKORDER_SPLIT_ID +'/' + C.WORKORDER_SUB_ID */ 
								
								, dbo.sfnWONUMFormat(C.WORKORDER_BASE_ID, 
                                C.WORKORDER_LOT_ID, C.WORKORDER_SPLIT_ID, C.WORKORDER_SUB_ID) AS CURRENT_WO_ID, dbo.sfnWONUMFormat_OLD(C.WORKORDER_BASE_ID, C.WORKORDER_LOT_ID, C.WORKORDER_SPLIT_ID, 
                                C.WORKORDER_SUB_ID) AS OLD_WO_ID, sc.CUSTOMER_ID
      FROM            CO_PRODUCT C 
	  LEFT JOIN
                                ShipperContents sc ON sc.SUPPLY_BASE_ID = C.WORKORDER_BASE_ID AND sc.SUPPLY_LOT_ID = C.WORKORDER_LOT_ID AND sc.SUPPLY_SUB_ID = C.WORKORDER_SUB_ID AND 
                                sc.SUPPLY_SPLIT_ID = C.WORKORDER_SPLIT_ID AND c.WORKORDER_TYPE = 'W' AND c.PART_ID = sc.PART_ID
      WHERE        EXISTS
                                    ( SELECT        1
                                      FROM            WORKORDERS W 
									  JOIN         ShipperContents S ON W.BASE_ID IN
                                                                    (SELECT        ISNULL(SUPPLY_BASE_ID, LEFT(TRACE_ID, CHARINDEX('/'
																	, REPLACE(TRACE_ID, '.', '/')) - 1)))
                                      WHERE        C.WORKORDER_BASE_ID = W.BASE_ID AND C.WORKORDER_LOT_ID = W.LOT_ID
									  AND C.WORKORDER_SUB_ID = W.SUB_ID AND C.WORKORDER_SPLIT_ID = W.SPLIT_ID
									  )
						)  ---- exists
, WORKORDER_OPS_BREAKDOWN AS
    (/*GET SPLITS -LINKED AND UNLINKED*/ 
	-- ~22
				SELECT 
				   null PACKLIST_IDx, 
				   sc.*, x.StepsFromChild, x.SequenceNo, x.BASE_ID, x.LOT_ID, x.SUB_ID
							   , x.SPLIT_ID AS SourceWO_SPLIT_ID/*col32*/ , ISNULL(WO.SPLIT_ID, WO2.SPLIT_ID) AS CURRENT_SPLIT_ID, 
											x.OPERATION_TYPE, x.RESOURCE_ID, x.SERVICE_ID
								
											/*, x.BASE_ID +'/'+ x.LOT_ID +'/'+ WO.SPLIT_ID+'/'+ x.SUB_ID */ 
								
											, ISNULL(sc.TRACE_ID, dbo.sfnWONUMFormat(x.BASE_ID, x.LOT_ID, WO.SPLIT_ID, x.SUB_ID)) 
											AS CURRENT_WO_ID
								
											/*, dbo.sfnWONUMFormat_OLD (x.BASE_ID, x.LOT_ID, WO.SPLIT_ID, x.SUB_ID ) AS OLD_WO_ID*/ 

											, 'main product' AS PartSource, CASE WHEN SUPPLY_BASE_ID IS NULL 
											THEN 'unlinked order' ELSE 'linked order' END AS FulfillmentMethod
				  FROM            ShipperContents sc 
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
					 null PACKLIST_IDx,
					 sc.*, 0, O.SEQUENCE_NO, WO.BASE_ID, WO.LOT_ID, WO.SUB_ID, WO.SPLIT_ID, WO.SPLIT_ID, O.OPERATION_TYPE, O.RESOURCE_ID, O.SERVICE_ID, ISNULL(sc.TRACE_ID, 
										   dbo.sfnWONUMFormat(WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID))
						/*, dbo.sfnWONUMFormat_OLD (WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID) */ 
						, 'main product' AS PartSource, 'unlinked order'
				  FROM            ShipperContents sc JOIN
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
				    null PACKLIST_IDx,
				    sc.*, 0, O.SEQUENCE_NO, WO.BASE_ID, WO.LOT_ID, WO.SUB_ID, WO.SPLIT_ID, WO.SPLIT_ID, O.OPERATION_TYPE, O.RESOURCE_ID
					, O.SERVICE_ID, dbo.sfnWONUMFormat(WO.BASE_ID, 
										   WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID)
										   /*, dbo.sfnWONUMFormat_OLD (WO.BASE_ID, WO.LOT_ID, WO.SPLIT_ID, WO.SUB_ID)*/ 
										   , 'main product' AS PartSource, 'linked order'
				  FROM            ShipperContents sc JOIN
										   WORKORDERS WO ON sc.SUPPLY_BASE_ID = WO.BASE_ID AND sc.SUPPLY_LOT_ID = WO.LOT_ID 
										   AND sc.SUPPLY_SUB_ID = WO.SUB_ID AND sc.SUPPLY_SPLIT_ID = WO.SPLIT_ID AND 
										   WO.COPY_FROM_SPLIT_ID IS NULL AND WO.PART_ID = sc.PART_ID 
										   /*ADDED TO PREVENT RETURN OF CO-PRODUCTS*/ 
										   JOIN
										   OPERATIONS O ON WO.BASE_ID = O.WORKORDER_BASE_ID AND WO.LOT_ID = O.WORKORDER_LOT_ID
										   AND WO.SUB_ID = O.WORKORDER_SUB_ID AND WO.SPLIT_ID = O.WORKORDER_SPLIT_ID AND 
										   WO.TYPE = O.WORKORDER_TYPE
				) -- WORKORDER_OPS_BREAKDOWN
, CustomerInfo AS
    (SELECT        ca.*, C.ID AS CUST_ID, ISNULL(C.NAME, NULL) AS SOLDTO_NAME, ISNULL(C.ADDR_1, NULL) AS SOLDTO_ADDR1, ISNULL(C.ADDR_2, NULL) AS SOLDTO_ADDR2, ISNULL(C.CITY, NULL) AS SOLDTO_CITY, 
                                ISNULL(C.STATE, NULL) AS SOLDTO_STATE, ISNULL(C.ZIPCODE, NULL) AS SOLDTO_ZIPCODE
      FROM            (SELECT        TOP 1 CUSTOMER_ID, SHIP_TO_ADDR_NO
                                FROM            ShipperContents) sc JOIN
                                CUST_ADDRESS ca ON sc.CUSTOMER_ID = ca.CUSTOMER_ID AND ca.ADDR_NO = sc.SHIP_TO_ADDR_NO JOIN
                                CUSTOMER C ON sc.CUSTOMER_ID = C.ID)
								
, Trace_Info AS
    (SELECT        IT.WORKORDER_BASE_ID, IT.WORKORDER_LOT_ID, IT.WORKORDER_SUB_ID, IT.WORKORDER_SPLIT_ID, IT.WORKORDER_TYPE
	               , IT.OPERATION_SEQ_NO, IT.REQ_PIECE_NO, sc.TRACE_ID, sc.PART_ID, 
                    T .APROPERTY_1, TP.APROPERTY_LABEL_1, T .APROPERTY_2, TP.APROPERTY_LABEL_2, T .APROPERTY_3, TP.APROPERTY_LABEL_3, T .APROPERTY_4, TP.APROPERTY_LABEL_4, T .APROPERTY_5, 
                                TP.APROPERTY_LABEL_5
      FROM            TRACE T 
	  JOIN
                 ShipperContents sc ON sc.PART_ID = T .PART_ID AND sc.TRACE_ID = T .ID 
					     JOIN
                                TRACE_PROFILE TP ON TP.PART_ID = sc.PART_ID JOIN
                                TRACE_INV_TRANS TRT ON TRT.TRACE_ID = T .ID JOIN
                                INVENTORY_TRANS IT ON TRT.TRANSACTION_ID = IT.TRANSACTION_ID
		) -- Trace_Info
 SELECT        w.*, r.PART_ID AS ResourcePART_ID, dbo.sfnSKILLS_WO_DOC_LINK_NO_LOC(w.BASE_ID, w.LOT_ID
               , w.SUB_ID, w.SourceWO_SPLIT_ID, 'W') AS SKILLS_WO_DOC_NO_LOC, dbo.sfnSKILLS_WO_DOC_LINK(w.BASE_ID, 
               w.LOT_ID, w.SUB_ID, w.SourceWO_SPLIT_ID, 'W') AS SKILLS_WO_DOC
			   , CASE WHEN r.PART_ID IS NULL THEN CASE WHEN w.RESOURCE_ID = 'rwec' 
			   THEN REPLACE(CONVERT(NVARCHAR(MAX), CONVERT(VARBINARY(MAX),
               oB.BITS)), 'Inspect', 'Inspected') ELSE CONVERT(NVARCHAR(MAX), CONVERT(VARBINARY(MAX), oB.BITS)) END ELSE NULL END AS Specs, CONVERT(NVARCHAR(MAX), CONVERT(VARBINARY(MAX), oB.BITS)) 
                              AS OperationDescription, CASE WHEN SCD.DESCRIPTION IS NULL AND w.SUPPLY_BASE_ID IS NOT NULL 
                              THEN 'See Attached Special Process Certificate of Performance for Skills PO: ' + w.SUPPLY_BASE_ID ELSE SCD.DESCRIPTION END AS DESCRIPTION, CASE WHEN w.RESOURCE_ID = 'Contractor' AND SER.ID IS NOT NULL 
                              AND LEFT(SER.DESCRIPTION, 3) IN ('FIN', 'SPL') THEN 'Y' WHEN SCD.DESCRIPTION IS NULL AND LEFT(SER.DESCRIPTION, 3) NOT IN ('FIN', 'SPL') THEN 'N' WHEN SCD.DESCRIPTION IS NULL AND SER.ID IS NULL 
                              THEN 'N' ELSE SCD.PRINT_ END AS 'PRINT_', ISNULL(ci.NAME, '') + CHAR(10) + CHAR(13) + ISNULL(ci.ADDR_1, '') + ' ' + ISNULL(ci.ADDR_2, '') + CHAR(10) + CHAR(13) + ISNULL(ci.CITY, '') + ' ' + ISNULL(ci.STATE, '') 
                              + ' ' + ISNULL(ci.ZIPCODE, '') + ' ' + ISNULL(ci.COUNTRY, '') AS SHIPTO, ISNULL(ci.SOLDTO_NAME, '') + CHAR(10) + CHAR(13) + ISNULL(ci.SOLDTO_ADDR1, '') + ' ' + ISNULL(ci.SOLDTO_ADDR2, '') + CHAR(10) + CHAR(13) 
                              + ISNULL(ci.SOLDTO_CITY, '') + ' ' + ISNULL(ci.SOLDTO_STATE, '') + ' ' + ISNULL(ci.SOLDTO_ZIPCODE, '') AS SOLDTO, ci.NAME, ci.ADDR_1, ci.ADDR_2, ci.ADDR_3, ci.CITY, ci.STATE, ci.ZIPCODE, ci.COUNTRY, 
                              ci.SALESREP_ID, RP.ID + ' ' + RP.DESCRIPTION AS COMPONENT, R.PIECE_NO, t .APROPERTY_LABEL_1 + ': ' + t .APROPERTY_1 AS PROPERTY_1, t .APROPERTY_LABEL_2 + ': ' + t .APROPERTY_2 AS PROPERTY_2, 
                              t .APROPERTY_LABEL_3 + ': ' + t .APROPERTY_3 AS PROPERTY_3
							  , t .APROPERTY_LABEL_4 + ': ' + t .APROPERTY_4 AS PROPERTY_4, dbo.sfnGetLastWOLocation(w.BASE_ID, w.LOT_ID, w.SUB_ID
							  , w.SourceWO_SPLIT_ID) 
                              AS SHIP_FROM
     FROM        WORKORDER_OPS_BREAKDOWN w 
	 JOIN
                  OPERATION_BINARY oB ON w.BASE_ID = oB.WORKORDER_BASE_ID AND w.LOT_ID = oB.WORKORDER_LOT_ID 
				  AND w.SUB_ID = oB.WORKORDER_SUB_ID AND w.SourceWO_SPLIT_ID = oB.WORKORDER_SPLIT_ID AND 
                  oB.WORKORDER_TYPE = 'W' AND w.SequenceNo = oB.SEQUENCE_NO 
	LEFT JOIN
                  SKILLS_CERT_DESC SCD ON w.OPERATION_TYPE = SCD.OP_TYPE JOIN
                  CustomerInfo ci ON ci.CUSTOMER_ID = w.CUSTOMER_ID LEFT JOIN
                              SERVICE SER ON w.SERVICE_ID = SER.ID 
							  LEFT JOIN
                              REQUIREMENT R ON w.BASE_ID = R.WORKORDER_BASE_ID AND w.LOT_ID = R.WORKORDER_LOT_ID AND w.SUB_ID = R.WORKORDER_SUB_ID 
							  AND w.SourceWO_SPLIT_ID = R.WORKORDER_SPLIT_ID AND 
                              R.WORKORDER_TYPE = 'W' AND w.RESOURCE_ID IN ('Stores', 'insp') AND r.OPERATION_SEQ_NO = w.SequenceNo 
							  AND R.SUBORD_WO_SUB_ID IS NULL AND EXISTS
                                  (SELECT        1
                                    FROM            PART
                                    WHERE        ID = R.PART_ID) LEFT JOIN
                              PART RP 
							  ON R.PART_ID = RP.ID 
							  LEFT JOIN
                                  (SELECT        IT.WORKORDER_BASE_ID, IT.WORKORDER_LOT_ID, IT.WORKORDER_SUB_ID, IT.WORKORDER_SPLIT_ID
								                 , IT.WORKORDER_TYPE, IT.OPERATION_SEQ_NO, IT.REQ_PIECE_NO, T .APROPERTY_1, 
                                                              TP.APROPERTY_LABEL_1, T .APROPERTY_2, TP.APROPERTY_LABEL_2, T .APROPERTY_3
															  , TP.APROPERTY_LABEL_3, T .APROPERTY_4, TP.APROPERTY_LABEL_4, T .APROPERTY_5, 
                                                              TP.APROPERTY_LABEL_5
                                    FROM            INVENTORY_TRANS IT JOIN
                                                              TRACE_INV_TRANS TRT ON IT.TRANSACTION_ID = TRT.TRANSACTION_ID JOIN
                                                              TRACE T ON TRT.TRACE_ID = T .ID JOIN
                                                              TRACE_PROFILE TP ON T .PART_ID = TP.PART_ID
                                    WHERE        EXISTS
                                            (SELECT        1
                                                FROM     WORKORDER_OPS_BREAKDOWN WO
                                                WHERE        WO.BASE_ID = IT.WORKORDER_BASE_ID AND WO.LOT_ID = IT.WORKORDER_LOT_ID AND WO.SUB_ID = IT.WORKORDER_SUB_ID AND 
                                                                       WO.CURRENT_SPLIT_ID = IT.WORKORDER_SPLIT_ID AND WO.SequenceNo = IT.OPERATION_SEQ_NO)
						           ) t
			           ON t .WORKORDER_BASE_ID = w.BASE_ID AND 
                              t .WORKORDER_LOT_ID = w.LOT_ID AND t .WORKORDER_SUB_ID = w.SUB_ID AND t .WORKORDER_SPLIT_ID = w.CURRENT_SPLIT_ID 
							  AND t .WORKORDER_TYPE = 'W' AND t .OPERATION_SEQ_NO = w.SequenceNo AND 
                              t .REQ_PIECE_NO = R.PIECE_NO
UNION ALL -- ~22
SELECT      1 x,  NULL, NULL, NULL, NULL, NULL, NULL, NULL, C.PART_ID, NULL, NULL/*col 10*/ , NULL, NULL, NULL, NULL, NULL
					, NULL, NULL AS USER_10, C.CUST_ORDER_ID, C.CUST_ORDER_LINE_NO, 
                         C.CUSTOMER_PART_ID AS CUST_PART_ID/*col20*/ , C.CUSTOMER_PO_REF, C.CUSTOMER_ID
						 , NULL, NULL, NULL AS CUST_POLN_PRINT, C.ShippedQTY, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 
                         C.CURRENT_WO_ID/*, C.OLD_WO_ID*/ , 'co-product', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
						 , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM            WORKORDER_COPRODUCTS C