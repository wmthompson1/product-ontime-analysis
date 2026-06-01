-- Purchase Order Status Summary
-- Lists all purchase orders with supplier name, type, status, and value.
-- Used for AP and procurement dashboards.
SELECT
    po.po_id,
    po.po_type,
    s.supplier_name,
    po.po_date,
    po.required_date,
    po.status,
    ROUND(po.total_cost, 2) AS total_cost
FROM purchase_order po
JOIN suppliers s ON po.supplier_id = s.supplier_id
ORDER BY po.po_date DESC
