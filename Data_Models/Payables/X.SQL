/**********************
Payables Data Model 1.2 flow intent null receiver 

payable status: L, H, P, X

-- SQL queries to explore data model relationships 
-- file path: Documentation/Data Models/Payables/

KB0731106

Purchase Receipt Accrual (PRA) reconciliation uses 3 reports:

1. Ledger > Post Manufacturing Journals > Reports > PO Accrual report:  Lists all Uninvoiced Receivers.
2. Admin > Costing Tools > File > P/O Accrual Analysis:  Compares Receivers to Invoices.
3. Payables > Invoice Entry > File > Print Uninvoiced Receipts:  Lists all Uninvoiced Receivers.


- po accrual: This should match to the balance in the Accounting Window for the PRA account

SELECT * FROM PAYABLE_LINE WHERE GL_ACCOUNT_ID = 'ENTER PO ACCRUAL ACCOUNT HERE' AND RECEIVER_ID IS NULL

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
IF OBJECT_ID('tempdb..#EDP') IS NOT NULL DROP TABLE #EDP
IF OBJECT_ID('tempdb..#EDF') IS NOT NULL DROP TABLE #EDF
IF OBJECT_ID('tempdb..#EDI') IS NOT NULL DROP TABLE #EDI


declare @AsOfDate datetime = convert(date, '2026-01-01');
DECLARE @VendorID nvarchar(15) = NULL;  -- set to specific vendor id or NULL for all
DECLARE @SiteID nvarchar(15) = NULL;    -- set to specific site id or NULL for all
-- Date window for data extracts (defaults to 1 month up to @AsOfDate)
DECLARE @StartDate DATE = @AsOfDate; --DATEADD(day, -3 , @AsOfDate);
DECLARE @EndDate DATE = getdate();
declare @topper int = 10000;  -- set to limit rows returned, or NULL for no limit
--
declare @RECEIVER_ID NVARCHAR(15) = NULL; --'215915'
declare @PURC_ORDER_ID NVARCHAR(15) = null; -- '184686';  -- 175717

declare @STATUS NVARCHAR(10) = NULL; 
declare @QTYISSUE NVARCHAR(10) = null; 
declare @PRICEISSUES NVARCHAR(10) = null; 
declare @APPROVAL NVARCHAR(20) = null; --- 'NEEDS APPROVAL,APPROVAL MET'; -- example: 'NEEDS APPROVAL' or 'APPROVAL MET'
declare @POID NVARCHAR(15) = '_Blank'; -- set to specific PO ID or '_Blank' for all     

SELECT CONVERT(NVARCHAR(15), pNo) AS pNo
  , fileID
INTO #EDP
FROM [SQL-LAB-1].dbRMS.dbo.tblPO;

SELECT id
  , [section]
  , CompanyID
INTO #EDF
FROM [SQL-LAB-1].dbRMS.dbo.tblFiles;

SELECT fileID
INTO #EDI
FROM [SQL-LAB-1].dbRMS.dbo.tblInvoice;

WITH 
--  EDP AS (SELECT pNo, fileID FROM #EDP)
-- ,EDF AS (SELECT id, [section], CompanyID FROM #EDF)
-- ,EDI AS (SELECT fileID FROM #EDI),
FLOW  AS (

SELECT top (@topper)
  PO.VENDOR_ID AS PO_VENDOR_ID,
        POL.PURC_ORDER_ID,
  RL.RECEIVER_ID AS FLOW_RECEIVER_ID,
        po.ORDER_DATE,
   RL.LINE_NO AS FLOW_RCVR_LINE,
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
        ,p.PAY_STATUS


	, EDP.pNo  EDP_PNO
	, EDF.[section] 
	, EDF.[CompanyID]

        , edp.fileID
        , EDF.[section] AS FILE_SECTION
        , EDF.[section] AS APPROVAL_SECTION

        , P.INVOICE_ID
        , PO.CREATE_DATE
        , PO.ID AS PO_ID
        , POL.LINE_NO AS [PO_LINE_NO]
        , PRL.PURC_REQ_ID AS PR_ID
        , PRL.LINE_NO AS PR_LINE
        , PL.VOUCHER_ID AS PL_VOUCHER_ID
        , PL.LINE_NO AS VOUCHER_LINE
        , RL.RECEIVER_ID AS [RECEIVER_ID]
        , RL.LINE_NO AS RCVR_LINE
        , R.RECEIVED_DATE
        , PO.VENDOR_ID AS VENDOR_ID
        , POL.ORDER_QTY AS POL_ORDERQTY
        , RL.RECEIVED_QTY AS RL_RECEIVEDQTY
        , POL.UNIT_PRICE AS POL_UNITPRICE
        , P.TOTAL_AMOUNT AS PAY_TOTALAMT
        , POL.TOTAL_AMT_ORDERED AS [PO_AMOUNT]
        , POL.TOTAL_AMT_RECVD AS [RECEIVED_AMOUNT]
        , PL.AMOUNT AS [INVOICE_AMOUNT]
        , PO.BUYER

        ,IIF(POL.ORDER_QTY = RL.RECEIVED_QTY, 'NO', 'YES') AS [QTY ISSUE]
        , CASE
            WHEN (POL.UNIT_PRICE * RL.RECEIVED_QTY) = P.TOTAL_AMOUNT THEN 'NO'
            ELSE 'YES'
        END AS [PRICE ISSUE]
        , CASE 
            WHEN POR.PURC_REQ_ID IS NULL AND EDP.pNo IS NULL THEN 'NEEDS APPROVAL'
            ELSE 'APPROVAL MET'
        END AS APPROVALCHECK
        , POR.PURC_REQ_ID AS POR_PURC_REQ_ID
        
-- purchase_order_flow
FROM Live.dbo.PURC_ORDER_LINE POL
INNER JOIN Live.dbo.PURCHASE_ORDER PO ON POL.PURC_ORDER_ID = PO.ID

-- purchase_order_flow -- > receiver_flow
LEFT JOIN Live.dbo.RECEIVER_LINE RL
ON POL.PURC_ORDER_ID = RL.PURC_ORDER_ID
AND POL.LINE_NO = RL.PURC_ORDER_LINE_NO 
AND RL.RECEIVED_QTY > 0 -- UPD 8/7

    LEFT JOIN Live.dbo.PART PART
    ON PART.ID = POL.PART_ID

    JOIN Live.dbo.VENDOR V
    ON PO.VENDOR_ID = V.ID
	and PO.VENDOR_ID != 'TMXDIV'

    LEFT JOIN Live.dbo.USER_DEF_FIELDS UD 
    ON POL.PART_ID = UD.DOCUMENT_ID 
    AND UD.ID = 'UDF-0000082' AND UD.PROGRAM_ID = 'VMPRTMNT'

-- PURC REQ FLOW 
    LEFT JOIN Live.dbo.PURC_ORDER_REQ POR
    ON POL.PURC_ORDER_ID = POR.PURC_ORD_ID
    AND POL.LINE_NO = POR.PURC_ORD_LINE_NO

    LEFT JOIN Live.dbo.PURC_REQ_LINE PRL
    ON POR.PURC_REQ_ID = PRL.PURC_REQ_ID
    AND POR.PURC_REQ_LINE_NO = PRL.LINE_NO

    LEFT JOIN Live.dbo.RECEIVER R
    ON R.ID = RL.RECEIVER_ID




-- purchase_order_flow  -- > receiver_flow -- > payable_flow (via voucher)
LEFT JOIN Live.dbo.PAYABLE_LINE PL
  ON PL.RECEIVER_ID = RL.RECEIVER_ID
  AND PL.RECEIVER_LINE_NO = RL.LINE_NO

LEFT JOIN Live.dbo.PAYABLE P
  ON PL.VOUCHER_ID = P.VOUCHER_ID

LEFT JOIN #EDP EDP
 ON EDP.pNo = PO.ID

LEFT JOIN #EDF EDF
 ON EDF.id = EDP.fileID
 AND EDF.CompanyID = PO.VENDOR_ID
 AND EDF.[section] = 'Purchase Requisition'

LEFT JOIN #EDI EDI
 ON EDI.fileID = EDF.id


WHERE 1=1 
AND R.RECEIVED_DATE >= '2026-01-01'
--and RL.RECEIVER_ID is null
--AND RL.RECEIVER_ID = @RECEIVER_ID OR @RECEIVER_ID  IS NULL
and (pol.PURC_ORDER_ID = @PURC_ORDER_ID OR @PURC_ORDER_ID IS NULL)
--AND po.ORDER_DATE BETWEEN @StartDate AND @EndDate
)
,PAYABLE_FLOW AS (
SELECT * FROM FLOW f
WHERE 1=1 AND ( 
     (f.PAY_STATUS IN (@STATUS) OR @STATUS IS NULL)
    AND IIF(f.POL_ORDERQTY = f.RL_RECEIVEDQTY, 'NO','YES') IN (@QTYISSUE) OR @QTYISSUE IS NULL
    AND CASE
        WHEN (f.POL_UNITPRICE * f.RL_RECEIVEDQTY) = f.PAY_TOTALAMT THEN 'NO'
        ELSE 'YES'
    END IN (@PRICEISSUES) OR @PRICEISSUES IS NULL
    AND CASE 
        WHEN f.POR_PURC_REQ_ID IS NULL AND f.EDP_PNO IS NULL THEN 'NEEDS APPROVAL'
        ELSE 'APPROVAL MET'
    END IN (@APPROVAL) OR @APPROVAL IS NULL
    AND (@POID) = '_Blank'
    )
    OR f.PO_ID IN (@POID)
)       
SELECT * FROM PAYABLE_FLOW
WHERE 1=1       