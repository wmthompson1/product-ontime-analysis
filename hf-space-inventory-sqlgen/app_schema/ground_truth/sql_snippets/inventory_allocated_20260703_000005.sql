-- Allocated Quantity by Part — set-aware (open commitments only)
-- Total customer-order demand committed against on-hand stock, grouped by part.
-- Set semantics (per docs/mrp_set_semantics_criteria.md):
--   * ONLY customer_order.status = 'Open' lines count as live allocation.
--     Closed / Shipped / Cancelled orders are historical or void and are NOT
--     current commitments — including them overstates how much stock is spoken
--     for.  customer_order_line has no status of its own, so status is taken
--     from the parent customer_order via the join.
-- This is the headline (total open commitment) figure — it is the "allocated"
-- input the ATP snippet nets against on-hand + scheduled receipts.
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
JOIN customer_order o ON o.order_id = col.order_id
JOIN part p ON p.part_id = col.part_id
WHERE p.active = 1
  AND o.status = 'Open'
GROUP BY col.part_id, p.part_description, p.part_class, p.unit_of_measure, p.on_hand_qty
ORDER BY allocated_qty DESC
