# Payables — Invoice (INVOICE_ID) → Voucher Flow

This document explains how supplier invoice identifiers (`INVOICE_ID`) appear in the Payables data model and how they relate to receiver/receiving data. It extracts the authoritative schema details for `PAYABLE.INVOICE_ID` and `RECEIVER_LINE.INVOICE_ID`, shows typical join patterns, and gives safe recommendations for matching receiver records to payables/vouchers.

## Authoritative column definitions (excerpt)

- From `Documentation/Data Models/ddl/schema-extract/output/LIVE/dbo.PAYABLE.sql`:

```sql
[INVOICE_ID] NVARCHAR(20) DEFAULT  NOT NULL,
```

- From `Documentation/Data Models/ddl/schema-extract/output/LIVE/dbo.RECEIVER_LINE.sql`:

```sql
[INVOICE_ID] NVARCHAR(15) DEFAULT  NULL,
[INVOICED_DATE] datetime DEFAULT  NULL,
```

Notes:
- `PAYABLE.INVOICE_ID` is defined as `NVARCHAR(20)` and declared NOT NULL in the Live schema — the payable header always stores an invoice identifier when created.
- `RECEIVER_LINE.INVOICE_ID` is `NVARCHAR(15)` and nullable — receiver rows may optionally carry an invoice number recorded at receiving time (depends on business process).

## How invoice identifiers flow between receiving and payables

- Typical paths where invoice information is captured:
  - Receiver entry: `RECEIVER_LINE.INVOICE_ID` may be filled during receiving (if the supplier invoice number is known and the business captures it at receipt).
  - Invoice entry: AP Invoice creation inserts a `PAYABLE` header and `PAYABLE_LINE` rows. The AP entry stores the supplier invoice number in `PAYABLE.INVOICE_ID` and generates `PAYABLE.VOUCHER_ID` as the system identifier.
  - Matching: When invoices are matched to receivers (PO-based), the payable lines (`PAYABLE_LINE`) often reference the receiver (`RECEIVER_ID`, `RECEIVER_LINE_NO`) and/or the purchase order line (`PURC_ORDER_ID`, `PURC_ORDER_LINE_NO`). That link is the most reliable way to relate a receiver row to the payable that was created from it.

## Reliable join patterns

- Recommended: join via `PAYABLE_LINE` using receiver identifiers (accurate for PO-based matching):

```sql
SELECT
  RL.RECEIVER_ID,
  RL.LINE_NO AS RCVR_LINE,
  RL.INVOICE_ID AS RCVR_INVOICE,
  P.VOUCHER_ID,
  P.INVOICE_ID AS PAYABLE_INVOICE,
  PL.LINE_NO AS PAYABLE_LINE_NO,
  PL.AMOUNT
FROM Live.dbo.RECEIVER_LINE RL
JOIN Live.dbo.PAYABLE_LINE PL
  ON PL.RECEIVER_ID = RL.RECEIVER_ID
  AND PL.RECEIVER_LINE_NO = RL.LINE_NO
JOIN Live.dbo.PAYABLE P
  ON PL.VOUCHER_ID = P.VOUCHER_ID
WHERE RL.INVOICE_ID IS NOT NULL
  AND P.POSTING_DATE BETWEEN @StartDate AND @EndDate;
```

-- Alternate (less reliable) — match by invoice number only (use caution; include vendor/site):

Note: in our payable perspective `RECEIVER_LINE.INVOICE_ID` is often kept NULL, so the invoice-number-only match is not implemented by default. Also, `PAYABLE.INVOICE_ID` maps to the `Doc` field in the AP Automation (AP_App) ingestion schema — treat AP_App columns as a separate source when reconciling across systems.

```sql
-- Only use when receiver→payable_line linking is unavailable AND you know receiver rows carry invoice numbers.
SELECT RL.RECEIVER_ID, RL.LINE_NO, RL.INVOICE_ID AS RCVR_INV,
       P.VOUCHER_ID, P.INVOICE_ID AS PAY_INV, P.VENDOR_ID
FROM Live.dbo.RECEIVER_LINE RL
LEFT JOIN Live.dbo.PAYABLE P
  ON P.INVOICE_ID = CAST(RL.INVOICE_ID AS NVARCHAR(20))
     AND P.VENDOR_ID = @VendorID -- include vendor to reduce false matches
WHERE RL.INVOICE_ID IS NOT NULL;
```

Use this only when receiver → payable line linking is not available; invoice numbers are not guaranteed unique across vendors or time windows. Because `RECEIVER_LINE.INVOICE_ID` is frequently null in practice, prefer the `PAYABLE_LINE`-based joins above.

## Common business rules and cautions

- Length and data type differences: `RECEIVER_LINE.INVOICE_ID` (15 chars) vs `PAYABLE.INVOICE_ID` (20 chars). When matching by number, normalize/cast types and trim whitespace.
- Nullability: `RECEIVER_LINE.INVOICE_ID` may be empty; do not assume every receiver row carries an invoice number.
- Matching ambiguity: invoice numbers can repeat across vendors; always include vendor (and site) or date windows when matching by invoice number.
- Prefer system keys: `VOUCHER_ID` (on `PAYABLE`) and `RECEIVER_ID` + `LINE_NO` (on `RECEIVER_LINE`) are more reliable for linking related records than supplier-provided invoice numbers.

## Example: reconcile receivers to vouchers (practical checklist)

1. Try to join `RECEIVER_LINE` → `PAYABLE_LINE` by `RECEIVER_ID` + `RECEIVER_LINE_NO` → then `PAYABLE` via `VOUCHER_ID`.
2. If that mapping returns no rows, attempt a cautious invoice-number match with `P.VENDOR_ID` and a date window filter.
3. Report any unmatched receiver rows for manual review — missing payables could indicate pending invoice entry or a processing error.

## Where this lives
- File: `Documentation/Data Models/Payables/payables_invoice_voucher_flow.md` (this document).
- Authoritative DDLs: `Documentation/Data Models/ddl/schema-extract/output/LIVE/dbo.PAYABLE.sql`, `.../dbo.PAYABLE_LINE.sql`, `.../dbo.RECEIVER_LINE.sql`.

_If you want, I can also add a short query that exports unmatched receiver rows (no linked payable) for use as an exception report._
