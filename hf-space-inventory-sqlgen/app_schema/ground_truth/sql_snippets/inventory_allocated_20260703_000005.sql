-- Allocated Quantity by Part
-- Total open customer-order demand committed against on-hand stock, grouped by part.
-- Covers all customer_order_line rows; join to part filters for active parts only.
-- Used to quantify how much of on-hand inventory is already spoken for before
-- accepting new commitments or placing replenishment orders.
SELECT
    col.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.on_hand_qty,
    ROUND(SUM(col.order_qty), 2)            AS allocated_qty,
    COUNT(DISTINCT col.order_id)            AS open_order_count,
    MIN(col.need_by_date)                   AS earliest_need_by
FROM customer_order_line col
JOIN part p ON p.part_id = col.part_id
WHERE p.active = 1
GROUP BY col.part_id, p.part_description, p.part_class, p.unit_of_measure, p.on_hand_qty
ORDER BY allocated_qty DESC
