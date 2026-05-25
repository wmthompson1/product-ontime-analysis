
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results


declare @AsOfDate datetime = convert(date, '2024-01-01');
DECLARE @VendorID nvarchar(15) = NULL;  -- set to specific vendor id or NULL for all
DECLARE @SiteID nvarchar(15) = NULL;    -- set to specific site id or NULL for all
-- Date window for data extracts (defaults to 1 month up to @AsOfDate)
DECLARE @StartDate DATE = DATEADD(day, -3 , @AsOfDate);
DECLARE @EndDate DATE = getdate();
declare @topper int = 1000000;  -- set to limit rows returned, or NULL for no limit


-- Invoice header → lines:
SELECT P.VOUCHER_ID, P.INVOICE_ID, PL.LINE_NO, PL.AMOUNT
FROM Live.dbo.PAYABLE P
JOIN Live.dbo.PAYABLE_LINE PL ON PL.VOUCHER_ID = P.VOUCHER_ID
WHERE 1=1
  AND (P.POSTING_DATE BETWEEN @StartDate AND @EndDate) 
-- and P.VENDOR_ID = @VendorID;


-- Voucher → payments applied:
SELECT P.VOUCHER_ID, P.INVOICE_ID, CDL.AMOUNT AS AppliedAmt, CD.CHECK_DATE
FROM Live.dbo.PAYABLE P
LEFT JOIN Live.dbo.CASH_DISBURSE_LINE CDL ON CDL.VOUCHER_ID = P.VOUCHER_ID
LEFT JOIN Live.dbo.CASH_DISBURSEMENT CD
  ON CD.BANK_ACCOUNT_ID = CDL.BANK_ACCOUNT_ID AND CD.CONTROL_NO = CDL.CONTROL_NO
WHERE 1=1
  AND (P.POSTING_DATE BETWEEN @StartDate AND @EndDate)
-- AND P.VOUCHER_ID = @VoucherId;

-- Voucher → GL distributions (posting lines):
SELECT P.VOUCHER_ID, PD.DIST_NO, PD.GL_ACCOUNT_ID, PD.AMOUNT
FROM Live.dbo.PAYABLE P
JOIN Live.dbo.PAYABLE_DIST PD ON PD.VOUCHER_ID = P.VOUCHER_ID
WHERE 1=1
  AND (P.POSTING_DATE BETWEEN @StartDate AND @EndDate);

-- Vendor lookup:
SELECT P.VOUCHER_ID, P.INVOICE_ID, V.ID, V.NAME
FROM Live.dbo.PAYABLE P
LEFT JOIN Live.dbo.VENDOR V ON P.VENDOR_ID = V.ID
WHERE 1=1
  AND (P.POSTING_DATE BETWEEN @StartDate AND @EndDate);