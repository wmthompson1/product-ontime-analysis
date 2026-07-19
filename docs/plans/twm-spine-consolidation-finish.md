# Finish TWM Spine Consolidation

## What & Why
The consolidated Three-Way Match Coverage view (flat spine, receipt/voucher row grain, boolean truth flags) is registered as governed ground truth but is not yet reachable from the Query Palette, and nothing yet proves the sibling exception views are consistent with it. Wire it into the palette and add a regression gate that derives the sibling populations as filters over the spine.

## Done looks like
- "Three-Way Match Coverage" appears in the Query Palette under the payables/supplier intent, runs with NULL-bound parameters, and returns the full 124-row coverage population with all five match states.
- The palette wiring survives a fresh database rebuild (bootstrap) — same idempotent migration pattern used for the Partial-Receipt Accrual palette entry.
- A regression test proves, against the live database: (a) the PRA view's population equals the spine filtered to its condition (received > 0, < ordered, live voucher coverage < received), and (b) the Uninvoiced Receipts population is consistent with the spine's Received-Uninvoiced rows for receipt-linked lines. Test fails closed on any drift.
- The known boundary is asserted, not hidden: voucher lines without a receipt-line linkage are excluded from the spine and remain the Exceptions view's concern.

## Out of scope
- Retiring or rewriting the sibling views (PRA, Uninvoiced Receipts, TWM Exceptions) — they stay as-is.
- FULL OUTER generalization of the spine (Unexpected_Receipt / Invoice_No_PO states) — separate future decision.
- No changes to the spine SQL itself and no re-registration (base-table set unchanged).

## Steps
1. **Palette block** — add a "Three-Way Match Coverage" query block to the governed supplier-performance query file, mirroring the spine snippet SQL and its temporal-parameter header; mind that inserting mid-file shifts the query indexes of later blocks.
2. **Selector wiring migration** — extend the existing idempotent demo-migration pattern (or a sibling migration wired into bootstrap) to register the palette entry in the intent-query table, remapping shifted indexes exactly as the PRA wiring did.
3. **Spine-parity regression test** — new test file deriving the PRA and Uninvoiced Receipts populations from the spine and comparing row sets against the sibling governed views; run gate-style as an individual file.
4. **Verify** — palette/selector tests plus the new regression test pass individually; app restart shows the new palette entry.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/payables_threewaymatchcoverage_20260708_000005.sql`
- `hf-space-inventory-sqlgen/app_schema/queries/supplier_performance.sql`
- `hf-space-inventory-sqlgen/migrations/add_partial_receipt_accrual_demo.py:230-270`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py`
- `hf-space-inventory-sqlgen/tests/test_ground_truth_selector.py`
