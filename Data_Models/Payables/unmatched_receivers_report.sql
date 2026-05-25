-- unmatched_receivers_report.sql
-- Find receiver lines that have no linked payable via PAYABLE_LINE -> PAYABLE
-- Adjust @StartDate/@EndDate and @VendorID as needed before running.

DECLARE @StartDate DATE = '2025-07-01';
DECLARE @EndDate DATE = GETDATE();
DECLARE @VendorID NVARCHAR(15) = NULL; -- optional filter

SELECT
  RL.RECEIVER_ID,
  RL.LINE_NO AS RECEIVER_LINE_NO,
  RL.PURC_ORDER_ID,
  RL.PURC_ORDER_LINE_NO,
  RL.INVOICE_ID AS RECEIVER_INVOICE_ID,
  RL.RECEIVED_QTY,
  R.RECEIVED_DATE
FROM Live.dbo.RECEIVER_LINE RL
INNER JOIN Live.dbo.RECEIVER R ON RL.RECEIVER_ID = R.ID
LEFT JOIN Live.dbo.PAYABLE_LINE PL
  ON PL.RECEIVER_ID = RL.RECEIVER_ID
  AND PL.RECEIVER_LINE_NO = RL.LINE_NO
LEFT JOIN Live.dbo.PAYABLE P
  ON PL.VOUCHER_ID = P.VOUCHER_ID
WHERE PL.VOUCHER_ID IS NULL
  AND R.RECEIVED_DATE BETWEEN @StartDate AND @EndDate
  AND (@VendorID IS NULL OR EXISTS (
       SELECT 1 FROM Live.dbo.PURCHASE_ORDER PO WHERE PO.ID = RL.PURC_ORDER_ID AND PO.VENDOR_ID = @VendorID
    ))
ORDER BY RL.PURC_ORDER_ID, RL.RECEIVER_ID, RL.LINE_NO;

-- Note: this report finds receiver lines that do not have a payable_line linking them to a voucher.
-- In environments where receiver rows do not always get linked (or invoice numbers are kept off receivers),
-- this report will help identify exceptions for manual review.
