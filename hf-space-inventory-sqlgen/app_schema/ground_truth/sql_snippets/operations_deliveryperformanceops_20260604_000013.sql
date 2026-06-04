-- Delivery Performance: Operations View
-- Computes inbound on-time receipt performance per purchase order by
-- comparing the actual receipt date to the PO required date.
-- Used by operations to track material delivery reliability and flag
-- overdue open POs for expediting.
SELECT
    po.po_id,
    po.supplier_id,
    s.supplier_name,
    po.po_type,
    po.po_date,
    po.required_date,
    po.status                                              AS po_status,
    po.total_cost,
    MAX(r.receipt_date)                                    AS last_receipt_date,
    CASE
        WHEN MAX(r.receipt_date) IS NOT NULL
             AND MAX(r.receipt_date) <= po.required_date   THEN 'On Time'
        WHEN MAX(r.receipt_date) IS NOT NULL
             AND MAX(r.receipt_date) >  po.required_date   THEN 'Late'
        WHEN MAX(r.receipt_date) IS NULL
             AND po.status NOT IN ('Cancelled', 'Closed')
             AND date('now') > po.required_date            THEN 'Overdue — No Receipt'
        WHEN MAX(r.receipt_date) IS NULL
             AND po.status NOT IN ('Cancelled', 'Closed')  THEN 'Open — Pending'
        ELSE 'N/A'
    END                                                    AS delivery_status
FROM purchase_order po
LEFT JOIN receiving r  ON r.po_id      = po.po_id
LEFT JOIN suppliers s  ON s.supplier_id = po.supplier_id
GROUP BY
    po.po_id, po.supplier_id, s.supplier_name, po.po_type,
    po.po_date, po.required_date, po.status, po.total_cost
ORDER BY
    CASE
        WHEN MAX(r.receipt_date) IS NULL
             AND po.status NOT IN ('Cancelled', 'Closed')
             AND date('now') > po.required_date            THEN 1
        WHEN MAX(r.receipt_date) IS NOT NULL
             AND MAX(r.receipt_date) > po.required_date    THEN 2
        ELSE 3
    END,
    po.required_date
