# Payables Data Models

This folder contains exploratory queries and documentation for the Payables data model.

## Schema Reference

For complete table definitions, relationships, and join patterns, see:
- **[Payables Tables Reference](../../Schema/PAYABLES_TABLES.md)** - Comprehensive schema documentation with ER diagrams

### Quick DDL Links
Key payables table definitions:
- [PAYABLE](../../Schema/Tables/dbo.PAYABLE.sql) - Invoice header
- [PAYABLE_LINE](../../Schema/Tables/dbo.PAYABLE_LINE.sql) - Invoice line items
- [PAYABLE_DIST](../../Schema/Tables/dbo.PAYABLE_DIST.sql) - GL distributions
- [RECEIVER](../../Schema/Tables/dbo.RECEIVER.sql) / [RECEIVER_LINE](../../Schema/Tables/dbo.RECEIVER_LINE.sql) - Goods receipts
- [PURCHASE_ORDER](../../Schema/Tables/dbo.PURCHASE_ORDER.sql) / [PURC_ORDER_LINE](../../Schema/Tables/dbo.PURC_ORDER_LINE.sql) - Purchase orders
- [VENDOR](../../Schema/Tables/dbo.VENDOR.sql) - Vendor master
- [CASH_DISBURSE_LINE](../../Schema/Tables/dbo.CASH_DISBURSE_LINE.sql) - Payments

## Query Examples

Files:

- `Payables_Data_Model1.sql` — Invoice-level extracts, aging summaries, payment remittance examples, and batching patterns for large joins.
- `Payables_Data_Model2.sql` — Receiver-to-PO reconciliation and supplier/receiver perspective queries (receiver grain analysis).
- `Payables_Data_Model3-6.sql` — Additional payables queries (historic and variations).
- `payables_invoice_voucher_flow.md` — Authoritative mapping and recommended joins: `RECEIVER_LINE` → `PAYABLE_LINE` → `PAYABLE`, DDL excerpts and caveats (invoice-number matching, AP_App note).
- `unmatched_receivers_report.sql` — Exception report (lists receiver rows without an associated payable) — (created by documentation team)

Notes:
- Prefer `PAYABLE_LINE`-based joins (using `RECEIVER_ID` + `RECEIVER_LINE_NO`) to link receivers to payables. Matching only by invoice number is less reliable; refer to `payables_invoice_voucher_flow.md` for guidance.
