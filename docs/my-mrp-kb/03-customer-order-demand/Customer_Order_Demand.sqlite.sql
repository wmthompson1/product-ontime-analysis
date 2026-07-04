/*
Customer Order Demand — SQLite grounding query (SYNTHETIC).

This is the runnable SQLite query set that grounds the companion document
"Customer Order Demand - Aerospace MRP.md". It is rooted in the DEMAND
(Customer Order) perspective: customer_order joined to customer_order_line,
with part availability used only for the ATP-style derivation.

Per project convention the synthetic target dialect is SQLite (manufacturing.db).
The real Infor VISUAL T-SQL (Live.dbo.CUST_ORDER_LINE, DEMAND_SUPPLY_LINK,
WORK_ORDER) and the attached Manufacturing Demand Guide are faithful reference
benchmarks ONLY — not the synthetic target.

Ground-truth (Live.dbo.*, T-SQL)        ->  stand-in (manufacturing.db, SQLite)
  CUSTOMER_ORDER                          ->  customer_order            (demand header)
  CUST_ORDER_LINE                         ->  customer_order_line       (demand detail)
  PART (qty_on_hand)                       ->  part.on_hand_qty          (availability)
  CUST_ORDER_LINE.ORDER_QTY               ->  customer_order_line.order_qty
  CUST_ORDER_LINE.UNIT_PRICE              ->  customer_order_line.unit_price
  CUST_ORDER.STATUS                       ->  customer_order.status (Open/Shipped/Closed/Cancelled)

Join key: customer_order_line.order_id = customer_order.order_id.

IMPORTANT — where the synthetic model is THINNER than the real ERP reference:
  * No DEMAND_SUPPLY_LINK table — there is no stored bridge from a demand line to
    a supply (work order) record, so "allocated" is DERIVED (open-order demand),
    not read from a link table.
  * No desired/promised ship-date columns — only customer_order.order_date exists.
  * No per-LINE shipped / open / allocated quantity — status lives on the ORDER
    header (customer_order.status), not the line, so "open demand" = lines whose
    parent order status = 'Open'.
  * No unit-of-measure conversion — there is no stock-UoM vs user-UoM split on the
    order line; order_qty is taken as-is.
See the companion document's "Synthetic vs. real ERP" table for the full mapping.

----------------------------------------------------------------------
QUERY 1 — Customer-order demand register (customer_order ⋈ customer_order_line).
One row per order line: who ordered, when, the line's part and quantity, the
unit price, and the extended line value (order_qty * unit_price). This is the
raw demand picture before any availability check.
----------------------------------------------------------------------
*/

SELECT
    co.order_id,
    co.customer_name,
    co.order_date,
    co.status                                   AS order_status,
    col.line_no,
    col.part_id,
    col.order_qty,
    col.unit_price,
    ROUND(col.order_qty * col.unit_price, 2)    AS line_value
FROM customer_order co
JOIN customer_order_line col
    ON col.order_id = co.order_id
ORDER BY co.order_id, col.line_no;

/*
----------------------------------------------------------------------
QUERY 2 — ATP-style availability (DERIVED allocation).
For every part that has OPEN demand, compare physical stock (part.on_hand_qty)
against the open-order demand for that part. Because the synthetic model has no
allocated-quantity column, "allocated" is derived as the sum of order_qty on
lines whose parent order is still 'Open'.

    ATP = on_hand_qty - SUM(open order_qty)

A negative ATP would flag a shortage (demand exceeds free stock); a positive ATP
means the open demand is currently coverable from stock.
----------------------------------------------------------------------
*/

WITH open_demand AS (
    SELECT
        col.part_id,
        SUM(col.order_qty) AS open_qty,
        COUNT(*)           AS open_lines
    FROM customer_order co
    JOIN customer_order_line col
        ON col.order_id = co.order_id
    WHERE co.status = 'Open'
    GROUP BY col.part_id
)
SELECT
    p.part_id,
    p.part_description,
    p.on_hand_qty,
    d.open_lines,
    d.open_qty                                       AS allocated_open_demand,
    ROUND(p.on_hand_qty - d.open_qty, 1)             AS atp,
    CASE WHEN p.on_hand_qty - d.open_qty < 0
         THEN 'SHORTAGE' ELSE 'covered' END          AS atp_flag
FROM open_demand d
JOIN part p
    ON p.part_id = d.part_id
ORDER BY atp ASC;

/*
----------------------------------------------------------------------
QUERY 3 — Running total of demand by part (the cumulative-pressure view).
Mirrors the reference guide's "running total of open quantity by part and date".
Strictly customer_order ⋈ customer_order_line. For each part, walk its order
lines in date order and accumulate order_qty, so you can see demand build up
over time rather than line-by-line. (Real ERP would run this on open lines by
desired ship date; the synthetic model has only order_date and order-level
status, so we order by order_date.)
----------------------------------------------------------------------
*/

SELECT
    col.part_id,
    co.order_id,
    co.order_date,
    co.status                                       AS order_status,
    col.order_qty,
    SUM(col.order_qty) OVER (
        PARTITION BY col.part_id
        ORDER BY co.order_date, co.order_id, col.line_no
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                               AS running_qty_for_part
FROM customer_order co
JOIN customer_order_line col
    ON col.order_id = co.order_id
ORDER BY col.part_id, co.order_date, co.order_id, col.line_no;
