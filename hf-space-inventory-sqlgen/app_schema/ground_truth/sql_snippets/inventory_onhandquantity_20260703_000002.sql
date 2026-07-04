-- On-Hand Stock Levels by Part Class
-- Summarises current physical inventory quantity and value by part class.
-- Flags part classes where any items have fallen below their reorder point.
-- Used for inventory visibility, cycle-count planning, and finance reporting.
SELECT
    p.part_class,
    COUNT(*)                                                          AS part_count,
    ROUND(SUM(p.on_hand_qty), 2)                                     AS total_on_hand,
    ROUND(SUM(p.on_hand_qty * p.unit_cost), 2)                       AS inventory_value,
    SUM(CASE WHEN p.on_hand_qty <= 0                 THEN 1 ELSE 0 END) AS stockout_count,
    SUM(CASE WHEN p.on_hand_qty <= p.reorder_point
              AND p.on_hand_qty > 0                  THEN 1 ELSE 0 END) AS at_reorder_count,
    SUM(CASE WHEN p.on_hand_qty >  p.reorder_point   THEN 1 ELSE 0 END) AS adequate_count
FROM part p
WHERE p.active = 1
GROUP BY p.part_class
ORDER BY inventory_value DESC
