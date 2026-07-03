-- Available To Promise (ATP) by Part
-- Uncommitted on-hand stock per active part: on-hand quantity minus the total
-- quantity already committed to existing customer order lines (allocated demand).
-- A positive ATP means stock is available for new orders.
-- A negative ATP means open demand already exceeds on-hand supply.
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.on_hand_qty,
    COALESCE(agg.allocated_qty, 0)                                      AS allocated_qty,
    ROUND(p.on_hand_qty - COALESCE(agg.allocated_qty, 0), 2)           AS atp_qty,
    CASE
        WHEN p.on_hand_qty - COALESCE(agg.allocated_qty, 0) >= 0       THEN 'AVAILABLE'
        ELSE 'OVERCOMMITTED'
    END AS atp_status
FROM part p
LEFT JOIN (
    SELECT part_id, SUM(order_qty) AS allocated_qty
    FROM customer_order_line
    GROUP BY part_id
) agg ON agg.part_id = p.part_id
WHERE p.active = 1
ORDER BY atp_qty ASC
