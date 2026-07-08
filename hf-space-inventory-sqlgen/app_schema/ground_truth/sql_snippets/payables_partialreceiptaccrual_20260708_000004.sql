-- Partial-Receipt Accrual Exposure (purchase-order line accrual)
-- One row per PO LINE in the partial-receipt accrual condition from the TWM
-- accrual guides (docs/my-mrp-kb/07-three-way-match/):
--   "any PO line with receivedQty > 0 but < orderedQty will appear on the
--    Uninvoiced Receipts Detailed report until invoicedQty >= receivedQty"
-- i.e. received quantity is strictly greater than zero AND strictly less than
-- the ordered quantity, and the received portion is not yet fully covered by
-- non-cancelled payable (voucher) lines. The uncovered received quantity is
-- open Purchase Receipt Accrual (PRA) exposure: at receipt the ERP posts
-- DR Inventory / CR PRA, and the accrual is only relieved (DR PRA / CR AP)
-- when the invoice is matched. Expands the UNINVOICEDRECEIPTS view (receipt-
-- header exception grain) with the ordered-vs-received quantity mismatch at
-- PO-line grain.
--
-- Lineage (synthetic twin, SQLite manufacturing.db):
--   purchase_order -> po_line            (header -> ordered qty/price baseline)
--   purchase_order -> suppliers          (vendor enrichment)
--   po_line -> receiving_line            (receipt coverage via rl.po_line_id,
--                                         the strict 3WM line linkage;
--                                         aggregated in a derived table so the
--                                         PO-line grain never fans out)
--   po_line -> payable_line -> payables  (invoice coverage via pl2.po_line_id;
--                                         cancelled vouchers excluded)
--
-- Field descriptions (from the governed field_descriptions overlay):
--   query_name         Report label for this accrual exposure extract.
--   purc_order_id      Purchase order identifier (purchase_order.po_id).
--   po_line_id         Purchase order line identifier (po_line.line_id).
--   part_id            Part ordered on the line (po_line.part_id).
--   vendor_id          Unique identifier for each suppliers record
--                      (suppliers.supplier_id).
--   vendor_name        Human-readable name of the supplier
--                      (suppliers.supplier_name).
--   site_id            Links each purchase order to its related site
--                      (purchase_order.site_id).
--   qty_ordered        Ordered quantity on the PO line (po_line.quantity).
--   qty_received       Sum of receiving_line.quantity_received linked to the
--                      PO line — the receipt coverage.
--   qty_invoiced       Sum of ABS(payable_line.qty) on non-cancelled payables
--                      linked to the PO line — the voucher coverage.
--   qty_uninvoiced     Received quantity not yet covered by vouchers
--                      (qty_received - qty_invoiced, floored at 0); this is
--                      the open PRA quantity.
--   accrued_value      qty_uninvoiced * po_line.unit_cost — the PO-price
--                      valuation of open PRA. (The synthetic twin carries no
--                      FIFO cost layers, so PO unit cost is the deterministic
--                      valuation basis; FIFO/PRE variance handling stays a
--                      real-source concern.)
--   last_receipt_date  Most recent dock date among the line's receipts.
--
-- Parameters (every guard is "(:param IS NULL OR <predicate>)", so binding all
-- to NULL reproduces the full exposure population):
--   :supplier_id Restrict to a single vendor (suppliers.supplier_id).
--   :start_date  Horizon filter lower bound on receiving.received_date.
--   :end_date    Dual role: (1) horizon upper bound on receiving.received_date;
--                (2) netting snapshot on payables.invoice_date inside the
--                voucher-coverage aggregate, so coverage reflects only
--                vouchers on file as of :end_date.
-- Cancelled purchase orders are excluded — a cancelled PO is not a live
-- contractual baseline, so it carries no accrual exposure.
SELECT
    'Partial-Receipt Accrual Exposure'   AS query_name,
    po.po_id                             AS purc_order_id,
    pl.line_id                           AS po_line_id,
    pl.part_id                           AS part_id,
    s.supplier_id                        AS vendor_id,
    s.supplier_name                      AS vendor_name,
    po.site_id                           AS site_id,
    ROUND(pl.quantity, 1)                AS qty_ordered,
    ROUND(rcv.qty_received, 1)           AS qty_received,
    ROUND(COALESCE(inv.qty_invoiced, 0), 1) AS qty_invoiced,
    ROUND(rcv.qty_received - COALESCE(inv.qty_invoiced, 0), 1) AS qty_uninvoiced,
    ROUND((rcv.qty_received - COALESCE(inv.qty_invoiced, 0)) * pl.unit_cost, 2)
                                         AS accrued_value,
    rcv.last_receipt_date                AS last_receipt_date
FROM po_line pl
JOIN purchase_order po ON po.po_id = pl.po_id
JOIN suppliers s       ON s.supplier_id = po.supplier_id
JOIN (
    SELECT
        rl.po_line_id,
        SUM(rl.quantity_received) AS qty_received,
        MAX(r.received_date)      AS last_receipt_date
    FROM receiving_line rl
    JOIN receiving r ON r.receipt_id = rl.receipt_id
    WHERE (:start_date IS NULL OR r.received_date >= :start_date)
      AND (:end_date IS NULL OR r.received_date <= :end_date)
    GROUP BY rl.po_line_id
) rcv ON rcv.po_line_id = pl.line_id
LEFT JOIN (
    SELECT
        pl2.po_line_id,
        SUM(ABS(pl2.qty)) AS qty_invoiced
    FROM payable_line pl2
    JOIN payables pay ON pay.invoice_id = pl2.invoice_id
    WHERE pl2.po_line_id IS NOT NULL
      AND pay.status <> 'Cancelled'
      AND (:end_date IS NULL OR pay.invoice_date <= :end_date)
    GROUP BY pl2.po_line_id
) inv ON inv.po_line_id = pl.line_id
WHERE po.status <> 'Cancelled'
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
  AND rcv.qty_received > 0
  AND rcv.qty_received < pl.quantity
  AND COALESCE(inv.qty_invoiced, 0) < rcv.qty_received
ORDER BY s.supplier_id, po.po_id, pl.line_id ASC
