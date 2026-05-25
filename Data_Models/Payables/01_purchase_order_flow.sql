/**********************
Payables Data Model 1

-- looking for inovoices missing on the _visual side of join_
-- SQL queries to explore data model relationships 
-- file path: Documentation/Data Models/Payables/

**Common pitfalls / repo findings**
- `INVOICE_NO` appears in some reports and older queries — authoritative schema uses `INVOICE_ID`. Review each occurrence before bulk replacing.
- Some custom reports map `P.VOUCHER_ID = P.INVOICE_ID` for specific integrations (TMX); treat these as exceptions.

** payables_invoice_voucher_flow **
would you extract help file informaion on Invoice_id in payable perspective, from schema payable.Invoice_id and receiver_line.Invoice_id. 
this information can be placed in payables_invoice_voucher_flow

see Documentation/Data Models/Payables/payables_invoice_voucher_flow.md


**********************/


SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results


declare @AsOfDate datetime = convert(date, '2024-01-01');
DECLARE @VendorID nvarchar(15) = NULL;  -- set to specific vendor id or NULL for all
DECLARE @SiteID nvarchar(15) = NULL;    -- set to specific site id or NULL for all
-- Date window for data extracts (defaults to 1 month up to @AsOfDate)
DECLARE @StartDate DATE = DATEADD(day, -3 , @AsOfDate);
DECLARE @EndDate DATE = getdate();
declare @topper int = 1000;  -- set to limit rows returned, or NULL for no limit
--
declare @RECEIVER_ID NVARCHAR(15) = NULL; --'215915'
declare @PURC_ORDER_ID NVARCHAR(15) = null; -- '184686';  -- 175717

SELECT top (@topper)
        PO.VENDOR_ID,              
        POL.PURC_ORDER_ID,
        RL.RECEIVER_ID,
        po.ORDER_DATE,
         RL.LINE_NO AS RCVR_LINE,
        RL.INVOICE_ID AS RCVR_INVOICE,
        P.VOUCHER_ID,
        P.INVOICE_ID AS PAYABLE_INVOICE,
        PL.LINE_NO AS PAYABLE_LINE_NO,
        PL.AMOUNT,
        pol.DESIRED_RECV_DATE 
        , POL.COMMODITY_CODE
        --, CONVERT(DATE, POL.DESIRED_RECV_DATE + 5, 101) as 'DUE_DATE'
        , UD.STRING_VAL AS CONTROLLED
        , V.USER_6 as SUPPLIER_TYPE
        , POL.PART_ID
        , PART.PLANNER_USER_ID
        , V.user_7 as PRODUCT_TYPE
        ,rl.transaction_id
        ,P.VOUCHER_ID
        
-- purchase_order_flow
FROM PURC_ORDER_LINE POL
INNER JOIN PURCHASE_ORDER PO ON POL.PURC_ORDER_ID = PO.ID

-- purchase_order_flow -- > receiver_flow
left JOIN RECEIVER_LINE RL
ON POL.PURC_ORDER_ID = RL.PURC_ORDER_ID
AND POL.LINE_NO = RL.PURC_ORDER_LINE_NO 
AND RL.RECEIVED_QTY > 0 -- UPD 8/7

    left JOIN.PART 
    ON PART.ID = POL.PART_ID

    JOIN VENDOR V
    ON PO.VENDOR_ID = V.ID
	and PO.VENDOR_ID != 'TMXDIV'

    LEFT JOIN USER_DEF_FIELDS UD 
    ON POL.PART_ID = UD.DOCUMENT_ID 
    AND UD.ID = 'UDF-0000082' AND UD.PROGRAM_ID = 'VMPRTMNT'

-- purchase_order_flow  -- > receiver_flow -- > payable_flow (via voucher)
LEFT JOIN Live.dbo.PAYABLE_LINE PL
  ON PL.RECEIVER_ID = RL.RECEIVER_ID
  AND PL.RECEIVER_LINE_NO = RL.LINE_NO

LEFT JOIN Live.dbo.PAYABLE P
  ON PL.VOUCHER_ID = P.VOUCHER_ID


WHERE 1=1 

--and RL.RECEIVER_ID is null
--AND RL.RECEIVER_ID = @RECEIVER_ID OR @RECEIVER_ID  IS NULL
and pol.PURC_ORDER_ID = @PURC_ORDER_ID OR @PURC_ORDER_ID IS NULL
and RL.INVOICE_ID IS NULL
AND po.ORDER_DATE BETWEEN @StartDate AND @EndDate
