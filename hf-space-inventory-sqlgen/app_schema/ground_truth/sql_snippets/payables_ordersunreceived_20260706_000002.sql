-- Purchase Orders Unreceived or Short
-- One row per purchase order with at least one po_line not fully received:
-- lines_unreceived counts lines with nothing received, lines_short counts
-- partial coverage, qty_outstanding totals the open quantity clamped at zero
-- per line (an over-received line never offsets another line's shortage).
-- Coverage is computed line-by-line through receiving_line.po_line_id.
-- Cancelled POs are excluded. Used for expediting and open-order dashboards.
SELECT
    po.po_id,
    po.supplier_id,
    po.status,
    po.required_date,
    COUNT(pl.line_id) AS lines,
    SUM(CASE WHEN COALESCE(r.qty_recv, 0) <= 0 THEN 1 ELSE 0 END) AS lines_unreceived,
    SUM(CASE WHEN COALESCE(r.qty_recv, 0) > 0
              AND COALESCE(r.qty_recv, 0) < pl.quantity THEN 1 ELSE 0 END) AS lines_short,
    ROUND(SUM(MAX(pl.quantity - COALESCE(r.qty_recv, 0), 0)), 1) AS qty_outstanding
FROM purchase_order po
JOIN po_line pl ON pl.po_id = po.po_id
LEFT JOIN (
    SELECT
        rl.po_line_id,
        SUM(rl.quantity_received) AS qty_recv
    FROM receiving_line rl
    GROUP BY rl.po_line_id
) r ON r.po_line_id = pl.line_id
WHERE po.status <> 'Cancelled'
GROUP BY po.po_id
HAVING SUM(CASE WHEN COALESCE(r.qty_recv, 0) < pl.quantity THEN 1 ELSE 0 END) > 0
ORDER BY po.required_date
