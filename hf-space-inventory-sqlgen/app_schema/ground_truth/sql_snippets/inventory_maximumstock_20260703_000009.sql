/* Maximum Stock Quantity by Part — static min/max policy proxy */
/* In a min/max replenishment policy the maximum stock level is the upper
   replenishment target: reorder point plus the average historical
   replenishment quantity derived from purchase-order lines.
   Set semantics (per docs/mrp_set_semantics_criteria.md):
     * This is a STATIC scalar policy proxy — no planning horizon / time-phasing.
     * The historical PO population EXCLUDES Cancelled purchase orders (a
       cancelled PO was never a real replenishment and would bias the average).
       Open / Partial / Received / Closed POs all represent genuine placed
       orders and are retained.  po_line has no status of its own, so status is
       taken from the parent purchase_order via the join.
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
        pl.part_id,
        ROUND(AVG(pl.quantity), 2)  AS avg_po_qty,
        COUNT(*)                    AS po_line_count
    FROM po_line pl
    JOIN purchase_order po ON po.po_id = pl.po_id
    WHERE po.status <> 'Cancelled'
    GROUP BY pl.part_id
) pol ON pol.part_id = p.part_id
WHERE p.active = 1
ORDER BY maximum_stock_qty DESC
