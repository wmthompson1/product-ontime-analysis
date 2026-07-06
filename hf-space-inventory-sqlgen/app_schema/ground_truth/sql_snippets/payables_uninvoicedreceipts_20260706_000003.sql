-- Uninvoiced Receipts (three-way match exception report)
-- One row per receipt that has at least one receiving line NOT fully matched
-- to a payable: either the received quantity exceeds the payable quantity
-- linked to that line, or the line has no payable link at all. Supports the
-- 3WM project and doubles as a receipts/payables monitoring exception report.
--
-- Refactored for the synthetic twin (SQLite manufacturing.db) from the
-- private-repo ground truth "203 3WM Uninvoiced Receipts" (SQL Server):
--   RECEIVER            -> receiving            (header: receipt_id, receipt_date, po_id)
--   RECEIVER_LINE       -> receiving_line       (line: receipt_line_id, quantity_received)
--   PURCHASE_ORDER      -> purchase_order       (vendor + site enrichment)
--   VENDOR              -> suppliers            (supplier_id, supplier_name)
--   PAYABLE             -> payables             (header; VOUCHER_ID -> invoice_id)
--   PAYABLE_LINE        -> payable_line         (RECEIVER_ID + RECEIVER_LINE_NO
--                                                composite link -> receipt_line_id,
--                                                the twin's strict line linkage)
--   PAY_STATUS <> 'L','X' (landed-cost/canceled) -> payables.status <> 'Cancelled'
--   R.SITE_ID IN ('SK01')                        -> purchase_order.site_id = 'SITE-1'
--                                                   (receiving carries no site; site
--                                                   lives on the purchase order)
--
-- Lineage (solder-engine structural fingerprint mirrors this):
--   Receipt header:      purchase_order -> receiving -> receiving_line
--   Payable match check: receiving_line -> payable_line -> payables
--   Vendor enrichment:   purchase_order -> suppliers
--
-- Field descriptions (from the governed field_descriptions overlay):
--   query_name      Report label for this exception extract.
--   receiver_id     Receipt header identifier (receiving.receipt_id — unique
--                   identifier for each receiving record).
--   received_date   The receipt date for the receiving (receiving.receipt_date).
--   purc_order_id   Links each receiving to its related po (receiving.po_id).
--   vendor_id       Unique identifier for each suppliers record (suppliers.supplier_id).
--   vendor_name     Human-readable name of the supplier (suppliers.supplier_name).
--   site_id         Links each purchase order to its related site (purchase_order.site_id).
--
-- Join-driving columns in the exception logic:
--   receiving_line.quantity_received  Numeric quantity received recorded for each
--                                     receiving line (was RECEIVER_LINE.USER_RECEIVED_QTY).
--   receiving_line.receipt_line_id    Unique identifier for each receiving line record
--                                     (replaces the RECEIVER_ID + LINE_NO composite).
--   payable_line.qty                  Numeric quantity recorded for each payable line.
--   payable_line.receipt_line_id      Links each payable line to the receiving line it
--                                     matches (line-level three-way match).
--   payables.status                   The status of each payables record; cancelled
--                                     vouchers are excluded from match coverage.
--   payables.invoice_id               Voucher key anchoring the payable header/line
--                                     relationship (payable_line.invoice_id joins here).
SELECT DISTINCT
    'Uninvoiced Receipts' AS query_name,
    r.receipt_id          AS receiver_id,
    r.receipt_date        AS received_date,
    r.po_id               AS purc_order_id,
    s.supplier_id         AS vendor_id,
    s.supplier_name       AS vendor_name,
    po.site_id            AS site_id
FROM receiving r
JOIN receiving_line rl ON rl.receipt_id = r.receipt_id
JOIN purchase_order po ON po.po_id = r.po_id
JOIN suppliers s       ON s.supplier_id = po.supplier_id
WHERE (
        rl.quantity_received > (
            SELECT COALESCE(SUM(ABS(pl.qty)), 0)
            FROM payable_line pl
            JOIN payables pay ON pay.invoice_id = pl.invoice_id
            WHERE pl.receipt_line_id = rl.receipt_line_id
              AND pay.status <> 'Cancelled'
        )
        OR rl.receipt_line_id NOT IN (
            SELECT pl.receipt_line_id
            FROM payable_line pl
            JOIN payables pay ON pay.invoice_id = pl.invoice_id
            WHERE pl.receipt_line_id IS NOT NULL
              AND pay.status <> 'Cancelled'
        )
      )
  AND po.site_id = 'SITE-1'
ORDER BY s.supplier_id, po.site_id, r.receipt_date ASC
