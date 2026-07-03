-- Parts At or Below Reorder Point
-- Inventory replenishment planning view: identifies parts where on-hand stock
-- has fallen to or below the SME-approved reorder point threshold.
-- Used for MRP demand review and purchasing trigger decisions.
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.on_hand_qty,
    p.reorder_point,
    p.lead_time_days,
    ROUND(p.on_hand_qty - p.reorder_point, 2) AS qty_vs_reorder,
    CASE
        WHEN p.on_hand_qty <= 0            THEN 'STOCKOUT'
        WHEN p.on_hand_qty <= p.reorder_point THEN 'REORDER'
        ELSE 'OK'
    END AS replenishment_status
FROM part p
WHERE p.active = 1
ORDER BY (p.on_hand_qty - p.reorder_point) ASC
