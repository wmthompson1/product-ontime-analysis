USE LIVE
GO

DECLARE @STARTDATE DATE = '2/1/2020';
, @ENDDATE DATE = '3/1/2020';

/* ORIGINAL CODE
SELECT R.CUSTOMER_ID
	, C.[NAME]
	, C.SALESREP_ID
	, C.ACTIVE_FLAG
	, R.POSTING_DATE
	, R.INVOICE_ID
	, R.INVOICE_DATE
	, R.TOTAL_AMOUNT
	, R.PAID_AMOUNT
FROM LIVE.dbo.RECEIVABLE R
INNER JOIN LIVE.dbo.CUSTOMER C
ON R.CUSTOMER_ID = C.ID
WHERE R.POSTING_DATE >= '2019-01-01'
AND R.POSTING_DATE < '2020-01-01'
ORDER BY R.CUSTOMER_ID
, R.INVOICE_ID
*/

-- MONTHLY CUSTOMER RECEIVABLES
SELECT R.CUSTOMER_ID
	, C.[NAME]
	, C.SALESREP_ID
	, C.ACTIVE_FLAG
	, C.USER_9
	, MONTH(R.POSTING_DATE) AS POSTING_MONTH
	--, R.INVOICE_ID
	--, R.INVOICE_DATE
	, SUM(R.TOTAL_AMOUNT) AS TOTAL_AMOUNT
	, SUM(R.PAID_AMOUNT) AS PAID_AMOUNT
FROM LIVE.dbo.RECEIVABLE R
INNER JOIN LIVE.dbo.CUSTOMER C
ON R.CUSTOMER_ID = C.ID
WHERE R.POSTING_DATE >= @STARTDATE
AND R.POSTING_DATE < @ENDDATE
GROUP BY R.CUSTOMER_ID
	, C.[NAME]
	, C.SALESREP_ID
	, C.ACTIVE_FLAG
	, C.USER_9
	, MONTH(R.POSTING_DATE)
ORDER BY R.CUSTOMER_ID
	, C.[NAME]
	, C.SALESREP_ID
	, C.ACTIVE_FLAG
	, C.USER_9
	, MONTH(R.POSTING_DATE)
	;

DECLARE @STARTDATE DATE = '7/1/2025'
, @ENDDATE DATE = '9/30/2025';

--INVENTORY ISSUES
SELECT CASE 
		WHEN ID.DEMAND_SUPPLY_ID IS NULL THEN 'UNLINKED'
		WHEN ID.DEMAND_SUPPLY_ID IS NOT NULL THEN 'LINKED'
	END AS [ORDER]
	, *
FROM SHIPPER_LINE SL
INNER JOIN SHIPPER S
	ON S.PACKLIST_ID = SL.PACKLIST_ID
INNER JOIN RECEIVABLE_LINE RL
	ON RL.INVOICE_ID = S.INVOICE_ID
INNER JOIN RECEIVABLE R
	ON RL.INVOICE_ID = R.INVOICE_ID
--> links Shipper to CO
INNER JOIN LIVE.dbo.INVENTORY_TRANS IT 
	ON IT.TRANSACTION_ID = SL.TRANSACTION_ID
INNER JOIN LIVE.dbo.CUST_ORDER_LINE COL
	ON IT.CUST_ORDER_ID = COL.CUST_ORDER_ID
	AND IT.CUST_ORDER_LINE_NO = COL.LINE_NO
INNER JOIN LIVE.dbo.CUSTOMER_ORDER CO
	ON COL.CUST_ORDER_ID = CO.ID
INNER JOIN LIVE.dbo.CUSTOMER C
	ON CO.CUSTOMER_ID = C.ID
INNER JOIN LIVE.dbo.INV_TRANS_DIST ID
	ON IT.TRANSACTION_ID = ID.OUT_TRANS_ID 
--> Inventory Issued to Job
INNER JOIN LIVE.dbo.INVENTORY_TRANS I1
	ON ID.IN_TRANS_ID = I1.TRANSACTION_ID
--LEFT OUTER JOIN LIVE.dbo.OPERATION O
--	ON I1.WORKORDER_TYPE = O.WORKORDER_TYPE
--	AND I1.WORKORDER_BASE_ID = O.WORKORDER_BASE_ID
--	AND I1.WORKORDER_LOT_ID = O.WORKORDER_LOT_ID
--	AND I1.WORKORDER_SPLIT_ID = O.WORKORDER_SPLIT_ID
--LEFT OUTER JOIN LIVE.dbo.SHOP_RESOURCE SR
-- --	ON O.RESOURCE_ID = SR.ID
-- LEFT OUTER JOIN WORK_ORDER WO
-- 	ON WO.[TYPE] = O.WORKORDER_TYPE
-- 	AND WO.BASE_ID = O.WORKORDER_BASE_ID
-- 	AND WO.LOT_ID = O.WORKORDER_LOT_ID
-- 	AND WO.SPLIT_ID = O.WORKORDER_SPLIT_ID
-- 	AND WO.SUB_ID = O.WORKORDER_SUB_ID
 --LEFT OUTER JOIN LIVE.dbo.SKILLS_WO_REC_QTY S
	--ON O.WORKORDER_BASE_ID = S.BASE_ID
	--AND O.WORKORDER_LOT_ID = S.LOT_ID
	--AND O.WORKORDER_SPLIT_ID = S.SPLIT_ID
WHERE (IT.TRANSACTION_DATE >= @STARTDATE
		AND IT.TRANSACTION_DATE < @ENDDATE)
	-- AND WO.RECEIVED_QTY > 0  -- ?? only if want to filter to completed jobs
	-- AND SR.RESOURCE_TYPE = N'LABOR'  -- ?? only if want to filter to labor resources

	AND IT.CLASS = N'I'
	AND IT.[TYPE] = N'O'
;

-- Copilot examples for filtering by date range after July 2025
-- WHERE (IT.TRANSACTION_DATE >= '2025-07-01' AND IT.TRANSACTION_DATE < '2025-08-01')
-- AND IT.CLASS = N'I'
-- AND IT.[TYPE] = N'O'	
-- ;
-- END OF FILE
-- Copilot examples for filtering by date range after July 2025
SELECT
    R.CUSTOMER_ID,
    C.[NAME]         AS CUSTOMER_NAME,
    C.SALESREP_ID,
    C.ACTIVE_FLAG,
    R.POSTING_DATE,
    R.INVOICE_ID,
    R.INVOICE_DATE,
    R.TOTAL_AMOUNT,
    R.PAID_AMOUNT
FROM LIVE.dbo.RECEIVABLE R
JOIN LIVE.dbo.CUSTOMER C ON R.CUSTOMER_ID = C.ID
WHERE R.POSTING_DATE >= '2025-08-01'   -- first day after July 31, 2025
  AND R.POSTING_DATE <= GETDATE()      -- up to current timestamp
;


-- williamt - 2025-11-14;
-- PRB NBSP issue with BOE payment settlement date vs receivable packlist_id

	DECLARE @paysettledate DATE = '07/08/2025'
	SELECT *
	FROM LIVEAccounting.dbo.boe_pay_summary_history AS i 
		LEFT OUTER JOIN LIVE.dbo.RECEIVABLE_LINE AS rl
			ON  i.[supplier invoice num] = rl.PACKLIST_ID
	WHERE CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
		AND rl.PACKLIST_ID IS NULL
		AND i.[boeing purchase order num]<> 'NO PO INVOICE'
		;
-- About the column name artifact: Supplier Invoice&nbsp;#
-- That &nbsp; (non-breaking space) is an HTML entity that can show up when headers contain special spaces. To avoid brittle mappings:

-- In Advanced Editor → Output Columns, rename it to Supplier Invoice # (or SupplierInvoice).
-- Or fix the header in your PowerShell/CSV (ensure a plain space, not NBSP). You can also strip NBSP in a Derived Column if needed:

	FROM SHIPPER_LINE SL
INNER JOIN SHIPPER S
	ON S.PACKLIST_ID = SL.PACKLIST_ID
INNER JOIN RECEIVABLE_LINE RL
	ON RL.INVOICE_ID = S.INVOICE_ID
	AND RL.PACKLIST_ID = SL.PACKLIST_ID
INNER JOIN RECEIVABLE R
	ON RL.INVOICE_ID = R.INVOICE_ID

	WHERE CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
		AND rl.PACKLIST_ID IS NULL
		AND i.[boeing purchase order num]<> 'NO PO INVOICE'
		;

	--> Visual Enterprise Financial Reports > Receivable Reports > BOE_receivable_comparison
--DECLARE @startdate AS DATE = '3/27/2019'
--, @enddate AS DATE = '6/18/2019'
--, @paysettledate AS DATE = '6/18/2019'

IF EXISTS
	(SELECT * 
	FROM dbo.boe_pay_summary_history
	WHERE CONVERT(DATE, [payment settlement date]) = CONVERT(DATE,@paysettledate)
	)
	BEGIN
		WITH cte_match AS
			(SELECT '5-does not match Packlist ID not equal to NO PO INVOICE' as invoice_group
				, NULL AS INVOICE_ID
				, NULL AS INVOICE_DATE
				, rl.PACKLIST_ID
				, rl.CUST_ORDER_ID
				, NULL AS CUSTOMER_ID
				, rl.AMOUNT
				, rl.REFERENCE
				, i.[check/trace num]
				, i.[boeing invoice num]
				, i.[boeing purchase order num]
				, i.[supplier invoice num]
				, i.[invoice received date]
				, i.[invoice gross amt]
				, CASE 
					WHEN 0 <>  i.[invoice net amt] THEN 0 -  i.[invoice net amt]
					ELSE 0
				END AS invoice_diff
				, i.payment
			FROM LIVEAccounting.dbo.boe_pay_summary_history AS i 
				LEFT OUTER JOIN LIVE.dbo.RECEIVABLE_LINE AS rl
					ON  i.[supplier invoice num] = rl.PACKLIST_ID
			WHERE CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
				AND rl.PACKLIST_ID IS NULL
				AND i.[boeing purchase order num]<> 'NO PO INVOICE'
			UNION ALL
			SELECT '1-Matches Packlist ID and dollar amt' as invoice_group
				, r.INVOICE_ID
				, r.INVOICE_DATE
				, rl.PACKLIST_ID
				, rl.CUST_ORDER_ID
				, r.CUSTOMER_ID
				, rl.AMOUNT
				, rl.REFERENCE
				, i.[check/trace num]
				, i.[boeing invoice num]
				, i.[boeing purchase order num]
				, i.[supplier invoice num]
				, i.[invoice received date]
				, i.[invoice gross amt]
				, CASE 
					WHEN rl.AMOUNT <>  i.[invoice net amt] THEN rl.AMOUNT -  i.[invoice net amt]
					ELSE 0
				END AS invoice_diff
				, i.payment
			FROM   LIVE.dbo.RECEIVABLE_LINE AS rl
				INNER JOIN LIVE.dbo.RECEIVABLE AS r
					ON rl.INVOICE_ID = r.INVOICE_ID
				INNER JOIN LIVEAccounting.dbo.boe_pay_summary_history AS i
					ON rl.packlist_id = i.[supplier invoice num]
				INNER JOIN LIVE.DBO.CUST_ORDER_LINE COL
					ON RL.CUST_ORDER_ID = COL.CUST_ORDER_ID
					AND RL.CUST_ORDER_LINE_NO = COL.LINE_NO
					AND COL.PART_ID IS NOT NULL		 
			WHERE REPLACE(i.[supplier invoice num], '/', ',') NOT LIKE '%,%'
				AND  rl.AMOUNT =  i.[invoice net amt]
				AND (r.CUSTOMER_ID = ''
					OR r.customer_id = 'BOE605'
					OR r.customer_id = 'BOE609'
					OR r.customer_id = 'BOE610'
					OR r.customer_id = 'BOEPOP'
					OR r.customer_id = 'BOETRN')
				AND rl.packlist_id > '1'
				AND r.invoice_date >= @startdate
				AND r.invoice_date <=  @enddate
				AND CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
			-- get lines that are in the 2nd part of the supplier invoice num to match to the packlist id
--> tt20211117: Add CO to matching criteria
			UNION ALL
			SELECT '1B-Matches CO_ID and dollar amt' as invoice_group
				, r.INVOICE_ID
				, r.INVOICE_DATE
				, rl.PACKLIST_ID
				, rl.CUST_ORDER_ID
				, r.CUSTOMER_ID
				, rl.AMOUNT
				, rl.REFERENCE
				, i.[check/trace num]
				, i.[boeing invoice num]
				, i.[boeing purchase order num]
				, i.[supplier invoice num]
				, i.[invoice received date]
				, i.[invoice gross amt]
				, CASE 
					WHEN rl.AMOUNT <>  i.[invoice net amt] THEN rl.AMOUNT -  i.[invoice net amt]
					ELSE 0
				END AS invoice_diff
				, i.payment
			FROM   LIVE.dbo.RECEIVABLE_LINE AS rl
				INNER JOIN LIVE.dbo.RECEIVABLE AS r
					ON rl.INVOICE_ID = r.INVOICE_ID
				INNER JOIN LIVEAccounting.dbo.boe_pay_summary_history AS i
-->					ON rl.packlist_id = i.[supplier invoice num]
					ON rl.CUST_ORDER_ID = i.[supplier invoice num]
				INNER JOIN LIVE.DBO.CUST_ORDER_LINE COL
					ON RL.CUST_ORDER_ID = COL.CUST_ORDER_ID
					AND RL.CUST_ORDER_LINE_NO = COL.LINE_NO
					AND COL.PART_ID IS NOT NULL		 
			WHERE REPLACE(i.[supplier invoice num], '/', ',') NOT LIKE '%,%'
				AND  rl.AMOUNT =  i.[invoice net amt]
				AND (r.CUSTOMER_ID = ''
					OR r.customer_id = 'BOE605'
					OR r.customer_id = 'BOE609'
					OR r.customer_id = 'BOE610'
					OR r.customer_id = 'BOEPOP'
					OR r.customer_id = 'BOETRN')
				AND rl.packlist_id > '1'
				AND r.invoice_date >= @startdate
				AND r.invoice_date <=  @enddate
				AND CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
			-- get lines that are in the 2nd part of the supplier invoice num to match to the packlist id

			)

		, cte_nomatch_dollar as
			(SELECT DISTINCT i.[boeing invoice num]
			FROM LIVEAccounting.dbo.boe_pay_summary_history AS i
				LEFT OUTER JOIN cte_match m
					ON i.[boeing invoice num]= m.[boeing invoice num] 
					AND i.[invoice gross amt] =  M.[invoice gross amt]
			WHERE m.[boeing invoice num] IS NULL
				AND CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
			)

		SELECT invoice_group
			, INVOICE_ID
			, INVOICE_DATE
			, PACKLIST_ID
			, CUST_ORDER_ID
			, CUSTOMER_ID
			, AMOUNT
			, REFERENCE
			, [check/trace num]
			, [boeing invoice num]
			, [boeing purchase order num]
			, [supplier invoice num]
			, [invoice received date]
			, [invoice gross amt]
			, invoice_diff
			, payment
		FROM CTE_MATCH
		UNION ALL 
		SELECT '2-Matches Packlist ID and but not dollar amt' as invoice_group
			, r.INVOICE_ID
			, r.INVOICE_DATE
			, rl.PACKLIST_ID
			, rl.CUST_ORDER_ID
			, r.CUSTOMER_ID
			, rl.AMOUNT
			, rl.REFERENCE
			, i.[check/trace num]
			, i.[boeing invoice num]
			, i.[boeing purchase order num]
			, i.[supplier invoice num]
			, i.[invoice received date]
			, i.[invoice gross amt]
			, CASE 
				WHEN rl.amount <>  i.[invoice net amt] THEN rl.amount -  i.[invoice net amt]
				ELSE 0
			END AS invoice_diff
			, i.payment
		FROM LIVEAccounting.dbo.boe_pay_summary_history AS i
			INNER JOIN LIVE.dbo.RECEIVABLE_LINE AS rl
				ON  rl.PACKLIST_ID = i.[supplier invoice num]
				AND  rl.AMOUNT <> i.[invoice net amt]
			INNER JOIN LIVE.dbo.RECEIVABLE AS r
				ON rl.INVOICE_ID = r.INVOICE_ID
			INNER JOIN LIVE.DBO.CUST_ORDER_LINE COL
				ON RL.CUST_ORDER_ID = COL.CUST_ORDER_ID
				AND RL.CUST_ORDER_LINE_NO = COL.LINE_NO
				AND COL.PART_ID IS NOT NULL	
			INNER JOIN cte_nomatch_dollar nd
				ON nd.[boeing invoice num] = i.[boeing invoice num] 	 
		WHERE REPLACE(i.[supplier invoice num], '/', ',') not like '%,%'
			 and (r.CUSTOMER_ID = ''
				  OR r.CUSTOMER_ID = 'BOE605'
				  OR r.CUSTOMER_ID = 'BOE609'
				  OR r.CUSTOMER_ID = 'BOE610'
				  OR r.CUSTOMER_ID = 'BOEPOP'
				  OR r.CUSTOMER_ID = 'BOETRN')
			  AND rl.PACKLIST_ID > '1'
			  AND r.INVOICE_DATE >= @startdate
			  AND r.INVOICE_DATE <=  @enddate
			  AND CONVERT(DATE,i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
		UNION ALL 
		SELECT '3-Matches Packlist ID for right side' as invoice_group
			, r.INVOICE_ID
			, r.INVOICE_DATE
			, rl.PACKLIST_ID
			, rl.CUST_ORDER_ID
			, r.CUSTOMER_ID
			, rl.AMOUNT
			, rl.REFERENCE
			, i.[check/trace num]
			, i.[boeing invoice num]
			, i.[boeing purchase order num]
			, SUBSTRING(i.[supplier invoice num], CHARINDEX(',', REPLACE(i.[supplier invoice num], '/', ','))+1,LEN(i.[supplier invoice num])) AS [supplier invoice num]
			, i.[invoice received date]
			, i.[invoice gross amt]
			, CASE 
				WHEN rl.amount <>  i.[invoice net amt] THEN rl.amount -  i.[invoice net amt]
				ELSE 0
			END AS invoice_diff
			, i.payment 
		FROM LIVE.dbo.RECEIVABLE_LINE AS rl
			INNER JOIN LIVE.dbo.RECEIVABLE AS r
			ON rl.INVOICE_ID = r.INVOICE_ID
			INNER JOIN LIVEAccounting.dbo.boe_pay_summary_history AS i
				ON rl.packlist_id = 
					SUBSTRING(i.[supplier invoice num], CHARINDEX(',', REPLACE(i.[supplier invoice num], '/', ','))+1,LEN(i.[supplier invoice num]))
				AND rl.AMOUNT = i.[invoice net amt]
			INNER JOIN LIVE.DBO.CUST_ORDER_LINE COL
				ON RL.CUST_ORDER_ID = COL.CUST_ORDER_ID
				AND RL.CUST_ORDER_LINE_NO = COL.LINE_NO
				AND COL.PART_ID IS NOT NULL
			INNER JOIN cte_nomatch_dollar nd
				ON nd.[boeing invoice num] = i.[boeing invoice num] 
		WHERE REPLACE(i.[supplier invoice num], '/', ',')  like '%,%'
			AND  rl.AMOUNT =  i.[invoice net amt]
			AND (r.CUSTOMER_ID = ''
				OR r.CUSTOMER_ID = 'BOE605'
				OR r.CUSTOMER_ID = 'BOE609'
				OR r.CUSTOMER_ID = 'BOE610'
				OR r.CUSTOMER_ID = 'BOEPOP'
				OR r.CUSTOMER_ID = 'BOETRN')
			AND rl.PACKLIST_ID > '1'
			AND r.INVOICE_DATE >= @startdate
			AND r.INVOICE_DATE <=  @enddate
			AND CONVERT(DATE, i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
		UNION ALL 
		-- get lines that are in the 1st part of the supplier invoice num to match to the packlist id
		SELECT '4-Matches Packlist ID for left side' as invoice_group
			, r.INVOICE_ID
			, r.INVOICE_DATE
			, rl.PACKLIST_ID
			, rl.CUST_ORDER_ID
			, r.CUSTOMER_ID
			, rl.AMOUNT
			, rl.REFERENCE
			, i.[check/trace num]
			, i.[boeing invoice num]
			, i.[boeing purchase order num]
			, SUBSTRING(i.[supplier invoice num],0,charindex(',',replace(i.[supplier invoice num], '/', ','))) as [supplier invoice num]
			, i.[invoice received date]
			, i.[invoice gross amt]
			, CASE 
				WHEN rl.AMOUNT <>  i.[invoice net amt] THEN rl.AMOUNT -  i.[invoice net amt]
				ELSE 0
			END AS invoice_diff
			, i.payment
		FROM   live.dbo.receivable_line AS rl
			INNER JOIN LIVE.dbo.RECEIVABLE AS r
				ON rl.INVOICE_ID = r.INVOICE_ID
			INNER JOIN LIVEAccounting.dbo.boe_pay_summary_history AS i
				ON rl.packlist_id = 
				substring(i.[supplier invoice num],0,charindex(',',replace(i.[supplier invoice num], '/', ',')))
			INNER JOIN LIVE.DBO.CUST_ORDER_LINE COL
				ON RL.CUST_ORDER_ID = COL.CUST_ORDER_ID
				AND RL.CUST_ORDER_LINE_NO = COL.LINE_NO
				AND COL.PART_ID IS NOT NULL
			INNER JOIN cte_nomatch_dollar nd
				ON nd.[boeing invoice num] = i.[boeing invoice num] 
		WHERE REPLACE(i.[supplier invoice num], '/', ',')  like '%,%'
			AND (r.CUSTOMER_ID = ''
				OR r.CUSTOMER_ID = 'BOE605'
				OR r.CUSTOMER_ID= 'BOE609'
				OR r.CUSTOMER_ID= 'BOE610'
				OR r.CUSTOMER_ID= 'BOEPOP'
				OR r.CUSTOMER_ID= 'BOETRN')
			AND rl.PACKLIST_ID > '1'
			AND r.INVOICE_DATE >= @startdate
			AND r.INVOICE_DATE <=  @enddate
			AND  CONVERT(DATE,i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
		UNION ALL
		-- get lines that are not in visual and not equal to NO PO INVOICE
		SELECT '6-does not match Packlist ID is equal to NO PO INVOICE' as invoice_group
			, null as invoice_id
			, null as invoice_date
			, rl.packlist_id
			, rl.CUST_ORDER_ID
			, null as customer_id
			, 0 as amount
			, rl.reference
			, i.[check/trace num]
			, i.[boeing invoice num]
			, i.[boeing purchase order num]
			, i.[supplier invoice num]
			, i.[invoice received date]
			, i.[invoice gross amt]
			, CASE 
				WHEN 0 <>  i.[invoice net amt] THEN 0 -  i.[invoice net amt]
				ELSE 0
			END AS invoice_diff
			, i.payment
		FROM  LIVEAccounting.dbo.boe_pay_summary_history AS i 
			LEFT OUTER JOIN LIVE.dbo.RECEIVABLE_LINE AS rl
				ON  i.[supplier invoice num] =  rl.packlist_id
		WHERE CONVERT(DATE,i.[payment settlement date]) = CONVERT(DATE,@paysettledate)
			and rl.PACKLIST_ID is null
			and i.[boeing purchase order num]= 'NO PO INVOICE'
	END
ELSE
	BEGIN 
		SELECT NULL AS invoice_id
			, NULL AS invoice_date
			, NULL AS PACKLIST_ID
			, NULL AS CUSTOMER_ID
			, NULL AS AMOUNT
			, NULL AS REFERENCE
			, NULL AS [check/trace num]
			, NULL AS [boeing invoice num]
			, NULL AS [boeing purchase order num]
			, NULL AS  supplier_invoice_num_cleaned
			, NULL AS [invoice received date]
			, NULL AS [invoice gross amt]
	END
	;
	