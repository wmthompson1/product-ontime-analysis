/* Minimum Stock Quantity by Part */
/* In a min/max replenishment policy the minimum stock level is the
   reorder point — the floor below which a replenishment must be triggered.
   Parts currently below their minimum are highlighted for immediate action. */
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.reorder_point                                AS minimum_stock_qty,
    p.on_hand_qty,
    p.lead_time_days,
    ROUND(p.on_hand_qty - p.reorder_point, 2)     AS buffer_above_min,
    CASE
        WHEN p.on_hand_qty <= 0               THEN 'ZERO_STOCK'
        WHEN p.on_hand_qty < p.reorder_point  THEN 'BELOW_MINIMUM'
        WHEN p.on_hand_qty = p.reorder_point  THEN 'AT_MINIMUM'
        ELSE                                       'ABOVE_MINIMUM'
    END                                            AS min_stock_status
FROM part p
WHERE p.active = 1
ORDER BY buffer_above_min ASC
