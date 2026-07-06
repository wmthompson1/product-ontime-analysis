-- Purchase Orders Received (fully received)
-- One row per purchase order where EVERY po_line has receipt coverage >= its
-- ordered quantity, computed line-by-line through receiving_line.po_line_id
-- (the strict line linkage from the three-way match chain). Cancelled POs
-- are excluded. Used for procurement and receiving dashboards.
SELECT
    po.po_id,
    po.supplier_id,
    po.status,
    COUNT(pl.line_id)                     AS lines,
    ROUND(SUM(pl.quantity), 1)            AS qty_ordered,
    ROUND(SUM(COALESCE(r.qty_recv, 0)), 1) AS qty_received,
    MAX(r.last_receipt)                   AS last_receipt_date
FROM purchase_order po
JOIN po_line pl ON pl.po_id = po.po_id
LEFT JOIN (
    SELECT
        rl.po_line_id,
        SUM(rl.quantity_received) AS qty_recv,
        MAX(rc.receipt_date)      AS last_receipt
    FROM receiving_line rl
    JOIN receiving rc ON rc.receipt_id = rl.receipt_id
    GROUP BY rl.po_line_id
) r ON r.po_line_id = pl.line_id
WHERE po.status <> 'Cancelled'
GROUP BY po.po_id
HAVING MIN(CASE WHEN COALESCE(r.qty_recv, 0) >= pl.quantity THEN 1 ELSE 0 END) = 1
ORDER BY last_receipt_date DESC
