-- Monthly Orders vs Monthly Completed Orders — Customer perspective
-- Requested by management (Customer perspective): monthly orders compared to
-- monthly completed orders, NOT aggregated to a single total, for the period
-- 2025-01-01 .. 2025-12-31. Lineage: originated as a bar chart, so the shape
-- is one row per month (time buckets) with two series per bucket.
--
-- Definitions (governed):
--   orders_placed    = customer orders whose order_date falls in the month
--                      (all statuses — it was an order when it was placed).
--   orders_completed = customer orders with status Shipped or Closed whose
--                      completed_date falls in the month, regardless of when
--                      they were placed. completed_date is deterministic:
--                      order_date + MAX(part.lead_time_days) across the
--                      order's lines (see migrations/
--                      add_customer_order_completed_date.py).
-- Every month in the period is emitted, including zero months, so chart
-- buckets never silently disappear.
-- Dialect: SQLite (synthetic ERP, manufacturing.db).
WITH RECURSIVE months(month_start) AS (
    SELECT date('2025-01-01')
    UNION ALL
    SELECT date(month_start, '+1 month')
    FROM months
    WHERE month_start < date('2025-12-01')
),
placed AS (
    SELECT strftime('%Y-%m', order_date) AS ym,
           COUNT(*)                      AS n
    FROM customer_order
    WHERE date(order_date) >= '2025-01-01'
      AND date(order_date) <= '2025-12-31'
    GROUP BY ym
),
completed AS (
    SELECT strftime('%Y-%m', completed_date) AS ym,
           COUNT(*)                          AS n
    FROM customer_order
    WHERE status IN ('Shipped', 'Closed')
      AND date(completed_date) >= '2025-01-01'
      AND date(completed_date) <= '2025-12-31'
    GROUP BY ym
)
SELECT
    strftime('%Y-%m', m.month_start) AS order_month,
    COALESCE(p.n, 0)                 AS orders_placed,
    COALESCE(c.n, 0)                 AS orders_completed
FROM months m
LEFT JOIN placed    p ON p.ym = strftime('%Y-%m', m.month_start)
LEFT JOIN completed c ON c.ym = strftime('%Y-%m', m.month_start)
ORDER BY order_month
