/* Economic Order Quantity (EOQ) Proxy by Part — static empirical proxy */
/* Without explicit ordering-cost and holding-cost parameters in this schema,
   the average observed purchase-order line quantity is used as the EOQ proxy —
   it reflects the historically settled replenishment lot size for each part.
   Set semantics (per docs/mrp_set_semantics_criteria.md):
     * This is a STATIC scalar proxy — no planning horizon / time-phasing.
     * The historical PO population EXCLUDES Cancelled purchase orders (a
       cancelled PO was never a real order and would bias the empirical average).
       Open / Partial / Received / Closed POs all represent genuine placed
       orders and are retained.  po_line has no status of its own, so status is
       taken from the parent purchase_order via the join.
   Parts with no (non-cancelled) PO history fall back to the reorder point as a
   conservative minimum order size.  eoq_order_value = eoq_proxy x unit_cost. */
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.unit_cost,
    COALESCE(pol.avg_po_qty, p.reorder_point)                              AS eoq_proxy,
    COALESCE(pol.avg_po_qty, 0)                                            AS avg_historical_po_qty,
    COALESCE(pol.total_po_qty, 0)                                          AS total_historical_po_qty,
    COALESCE(pol.po_line_count, 0)                                         AS po_line_count,
    ROUND(
        COALESCE(pol.avg_po_qty, p.reorder_point) * p.unit_cost, 2
    )                                                                      AS eoq_order_value,
    CASE
        WHEN pol.po_line_count IS NULL
          OR pol.po_line_count = 0  THEN 'FALLBACK_TO_ROP'
        WHEN pol.po_line_count = 1  THEN 'SINGLE_PO_OBSERVATION'
        ELSE                             'MULTI_PO_AVERAGE'
    END                                                                    AS eoq_confidence
FROM part p
LEFT JOIN (
    SELECT
        pl.part_id,
        ROUND(AVG(pl.quantity), 2)  AS avg_po_qty,
        SUM(pl.quantity)            AS total_po_qty,
        COUNT(*)                    AS po_line_count
    FROM po_line pl
    JOIN purchase_order po ON po.po_id = pl.po_id
    WHERE po.status <> 'Cancelled'
    GROUP BY pl.part_id
) pol ON pol.part_id = p.part_id
WHERE p.active = 1
ORDER BY eoq_order_value DESC
