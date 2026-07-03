/* Economic Order Quantity (EOQ) Proxy by Part */
/* Without explicit ordering-cost and holding-cost parameters in this schema,
   the average observed purchase-order line quantity is used as the EOQ proxy —
   it reflects the historically settled replenishment lot size for each part.
   Parts with no PO history fall back to the reorder point as a conservative
   minimum order size.  eoq_order_value = eoq_proxy × unit_cost. */
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
        part_id,
        ROUND(AVG(quantity), 2)  AS avg_po_qty,
        SUM(quantity)            AS total_po_qty,
        COUNT(*)                 AS po_line_count
    FROM po_line
    GROUP BY part_id
) pol ON pol.part_id = p.part_id
WHERE p.active = 1
ORDER BY eoq_order_value DESC
