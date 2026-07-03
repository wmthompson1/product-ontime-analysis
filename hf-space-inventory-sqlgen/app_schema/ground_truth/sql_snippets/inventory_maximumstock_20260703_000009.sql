/* Maximum Stock Quantity by Part */
/* In a min/max replenishment policy the maximum stock level is the upper
   replenishment target: reorder point plus the average historical
   replenishment quantity derived from purchase-order lines.
   Parts already above their computed maximum may be over-stocked. */
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.reorder_point                                                         AS minimum_stock_qty,
    COALESCE(pol.avg_po_qty, 0)                                            AS avg_replenishment_qty,
    COALESCE(pol.po_line_count, 0)                                         AS po_line_count,
    ROUND(p.reorder_point + COALESCE(pol.avg_po_qty, 0), 2)               AS maximum_stock_qty,
    p.on_hand_qty,
    CASE
        WHEN p.on_hand_qty
             > ROUND(p.reorder_point + COALESCE(pol.avg_po_qty, 0), 2)
        THEN 'OVERSTOCKED'
        WHEN p.on_hand_qty < p.reorder_point
        THEN 'BELOW_MINIMUM'
        ELSE 'IN_RANGE'
    END                                                                     AS minmax_status
FROM part p
LEFT JOIN (
    SELECT
        part_id,
        ROUND(AVG(quantity), 2)  AS avg_po_qty,
        COUNT(*)                 AS po_line_count
    FROM po_line
    GROUP BY part_id
) pol ON pol.part_id = p.part_id
WHERE p.active = 1
ORDER BY maximum_stock_qty DESC
