Data Models (DDL) — Receivables-related tables

## Schema Reference

For complete table definitions, relationships, and join patterns, see:
- **[Receivables Tables Reference](../../Schema/RECEIVABLES_TABLES.md)** - Comprehensive schema documentation with ER diagrams

### Quick DDL Links
Key receivables table definitions:
- [RECEIVABLE](../../Schema/Tables/dbo.RECEIVABLE.sql) / [RECEIVABLE_LINE](../../Schema/Tables/dbo.RECEIVABLE_LINE.sql) - Customer invoices
- [SHIPPER](../../Schema/Tables/dbo.SHIPPER.sql) / [SHIPPER_LINE](../../Schema/Tables/dbo.SHIPPER_LINE.sql) - Shipments/packlists
- [CUSTOMER_ORDER](../../Schema/Tables/dbo.CUSTOMER_ORDER.sql) / [CUST_ORDER_LINE](../../Schema/Tables/dbo.CUST_ORDER_LINE.sql) - Sales orders
- [CUSTOMER](../../Schema/Tables/dbo.CUSTOMER.sql) - Customer master
- [INVENTORY_TRANS](../../Schema/Tables/dbo.INVENTORY_TRANS.sql) / [INV_TRANS_DIST](../../Schema/Tables/dbo.INV_TRANS_DIST.sql) - Inventory movements
- [CASH_RECEIPT_LINE](../../Schema/Tables/dbo.CASH_RECEIPT_LINE.sql) - Payment receipts

## Background

Authoritative replacement note (2025-12-05):
- The guessed DDL templates in this folder were replaced with authoritative CREATE scripts extracted from the `LIVE` database using the schema-extract tool.
- Source files: `Documentation/Data Models/ddl/schema-extract/output/LIVE/` (per-table scripts, e.g. `dbo.RECEIVABLE.sql`).
- Replaced files: `RECEIVABLE.sql`, `RECEIVABLE_LINE.sql`, `CUSTOMER.sql`, `SHIPPER.sql`, `SHIPPER_LINE.sql`, `INVENTORY_TRANS.sql`, `INV_TRANS_DIST.sql`, `CUST_ORDER_LINE.sql`, `CUSTOMER_ORDER.sql`.
- Originals backed up to: `Documentation/Data Models/ddl/templates_backup/`.

This folder contains initial DDL templates for tables referenced by `Receivables.sql`.

Purpose:
- Capture minimal column definitions (types and keys) for onboarding, documentation, and downstream data model work.
- Provide a starting point for generating full DDLs that can be validated against production.

Notes and assumptions:
- Column selections and types are inferred from usage in `Receivables.sql` (packlist id, invoice ids, dates, amounts, join keys).
- Many production columns, constraints, indexes and types are guessed; these templates must be validated and adjusted against the source database.
- Some original column names include non-breaking spaces and special characters; column names here are normalized to safe SQL identifiers.

Next steps:
1. Review each DDL with the DBAs and replace guessed types with authoritative types.
2. Add indexes and constraints (FKs) after confirming cardinality and performance needs.
3. Add a script to compare these DDLs to the live schema (or pull schema via `INFORMATION_SCHEMA`).

If you want, I can generate a script to pull the actual schema from the `LIVE` and `LIVEAccounting` databases (requires connection).
