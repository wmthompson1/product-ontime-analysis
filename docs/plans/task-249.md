---
title: Complete three-way match data chain
---
# Complete Three-Way Match Data Chain

## What & Why
The three-way match (purchase order ↔ receiver ↔ payable) needs complete, consistent data across all six tables: `purchase_order`, `po_line`, `receiving`, `receiving_line`, `payables`, `payable_line`. Today only 3 of 24 POs have receipts while 11 have invoices, so most invoices have no receiver leg, and only 6 of 29 payable lines link to a receipt line. This blocks a credible ThreeWayMatchState snippet and the three supplier_performance queries that depend on it.

## Done looks like
- Every Closed PO is fully received (receipt header + one receiving line per PO line) and carries a matched, mostly-paid invoice whose payable lines link to both the PO line and the receipt line, with amounts that reconcile exactly.
- Partial POs are partially received (short quantities or missing lines) with a mix of match outcomes.
- Distinct, non-empty populations exist and are query-visible:
  - **Unreceived POs** — Open POs with no receipts and no invoices
  - **Received + invoiced + matched** — clean three-way matches
  - **Invoiced, voucher pending** — invoice on file with `three_way_match_status = 'Pending'`, unpaid
  - **Received, not yet invoiced** — receiver leg present, no payable yet (voucher pending on the receiving side)
  - **At least one Exception** — a deliberate quantity or price mismatch, invoice Disputed
- The 8 currently invoice-only POs gain their missing receiver legs (or are deliberately kept as Pending-match cases), and all 29 existing payable lines link to receipt lines wherever a receipt now exists.
- A verification step proves it: population counts non-empty, invoice amount = sum of payable lines = matched PO-line totals, no dangling links, and the Three-Way Match queries in supplier_performance.sql return rows for every state.

## Out of scope
- No new PO headers (demo-scale bands stay intact); scale only through lines if ever needed.
- MRP-critical POs (`PO-MRP-BLK1..3`, `PO-MRP-P-10032`, `PO-CON-001`) stay completely untouched so the MRP grid does not shift.
- No inventory-ledger writes — receipts here do not create inventory transactions.
- No snippet authoring or `-- Binding:` wiring (separate SME work already documented in docs/pods).

## Steps
1. **Receipt backfill migration** — Deterministic, idempotent migration that creates receipt headers and per-PO-line receiving lines for Closed and Partial POs, deriving quantities and dates from existing PO data (never random), keeping the legacy denormalized receiving header consistent with its lines.
2. **Payables completion** — Repair and extend invoices and payable lines so every invoice reconciles line-for-line to PO lines and (where received) receipt lines; assign the match-status mix (Matched/Pending/Exception) and payment statuses to produce every population above, including one engineered mismatch exception.
3. **Wire into the rebuild chain** — Register the migration in the bootstrap/migration chain so a fresh clone reproduces the same data; updates must be additive/upsert-style so the startup schema re-seed cannot revert them.
4. **Verification gate** — Add a fail-closed check (script or test) covering population counts, amount reconciliation, linkage integrity, and that each supplier_performance three-way-match query returns rows; verify the live WAL-mode DB via sqlite3 dumps.
5. **Run the affected tests** — Execute the relevant test files gate-style (one file per run) to confirm nothing else regressed.

## Relevant files
- `hf-space-inventory-sqlgen/migrations/`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/app_schema/queries/supplier_performance.sql`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`