-- Open Purchase Orders by Supplier
-- Aggregates open PO value and order count per supplier.
-- Used for payables aging and supplier spend analysis.
SELECT
    s.supplier_name,
    s.certification_level,
    COUNT(po.po_id)         AS open_po_count,
    ROUND(SUM(po.total_cost), 2) AS total_open_value
FROM purchase_order po
JOIN suppliers s ON po.supplier_id = s.supplier_id
WHERE po.status IN ('Open', 'Received')
GROUP BY po.supplier_id, s.supplier_name, s.certification_level
ORDER BY total_open_value DESC
