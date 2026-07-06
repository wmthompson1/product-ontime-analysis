-- Ground Truth SQL: Receivables / Customer Order Revenue Queries
-- Perspective: Receivables
-- Category: receivables
-- Source: Manufacturing SQL Semantic Layer (Replit public repo)
--
-- NOTE ON FRAMING: there is no AR invoice ledger in this schema, so the
-- receivables view is read from the customer order book. The accounting
-- state of an order (OrderAccountingState concept, customer_order.status)
-- drives revenue recognition:
--   Closed    → revenue recognized (delivered and complete)
--   Shipped   → billable — shipped but not yet closed (unbilled AR exposure)
--   Open      → backlog — booked, not yet recognizable
--   Cancelled → excluded from all revenue roll-ups
--
-- Order value = SUM(order_qty × unit_price) over customer_order_line.
-- Aging is computed against a data-derived as-of date
-- (MAX(order_date) in the order book), never the wall clock.
--
-- Temporal binding key: :start_date (ISO date, optional order_date lower bound)

-- ============================================================
-- Query 1 — order_revenue_recognition
-- Intent:   How much order revenue sits in each accounting state?
-- Typical:  "Revenue recognition status of the order book"
--           "How much is recognized vs billable vs backlog?"
-- Params:   :start_date (optional)
-- Perspective: Receivables — the accounting roll-up of the order book
-- ============================================================
-- Query: Order Revenue Recognition Status
-- Description: How much order revenue sits in each accounting state? Order counts and line value grouped into recognized (Closed), billable (Shipped), and backlog (Open); Cancelled excluded.
SELECT
    CASE co.status
        WHEN 'Closed'  THEN 'Recognized'
        WHEN 'Shipped' THEN 'Billable — shipped, not closed'
        WHEN 'Open'    THEN 'Backlog — booked, not recognizable'
    END                                                         AS accounting_state,
    co.status                                                   AS order_status,
    COUNT(DISTINCT co.order_id)                                 AS order_count,
    ROUND(SUM(col.order_qty * col.unit_price), 2)               AS order_value
FROM customer_order co
JOIN customer_order_line col
    ON col.order_id = co.order_id
WHERE co.status IN ('Open', 'Shipped', 'Closed')
  AND (:start_date IS NULL OR co.order_date >= :start_date)
GROUP BY co.status
ORDER BY CASE co.status WHEN 'Closed' THEN 1 WHEN 'Shipped' THEN 2 ELSE 3 END;

-- ============================================================
-- Query 2 — customer_ar_exposure
-- Intent:   What is our receivables exposure by customer?
-- Typical:  "Which customers carry the most unbilled AR?"
--           "Customer exposure: billable vs backlog"
-- Params:   :start_date (optional)
-- Perspective: Receivables — exposure = shipped-but-not-closed value,
--           with booked backlog shown alongside
-- ============================================================
-- Query: Customer AR Exposure
-- Description: What is our receivables exposure by customer? Billable (shipped, not closed) value per customer, with open backlog and recognized revenue alongside.
SELECT
    co.customer_name,
    COUNT(DISTINCT co.order_id)                                 AS total_orders,
    ROUND(SUM(CASE WHEN co.status = 'Shipped'
                   THEN col.order_qty * col.unit_price
                   ELSE 0 END), 2)                              AS billable_exposure,
    ROUND(SUM(CASE WHEN co.status = 'Open'
                   THEN col.order_qty * col.unit_price
                   ELSE 0 END), 2)                              AS open_backlog,
    ROUND(SUM(CASE WHEN co.status = 'Closed'
                   THEN col.order_qty * col.unit_price
                   ELSE 0 END), 2)                              AS recognized_revenue
FROM customer_order co
JOIN customer_order_line col
    ON col.order_id = co.order_id
WHERE co.status IN ('Open', 'Shipped', 'Closed')
  AND (:start_date IS NULL OR co.order_date >= :start_date)
GROUP BY co.customer_name
ORDER BY billable_exposure DESC, open_backlog DESC;

-- ============================================================
-- Query 3 — open_order_backlog_aging
-- Intent:   How old is the open order backlog?
-- Typical:  "Backlog aging report"
--           "Which open orders have been sitting the longest?"
-- Params:   :start_date (optional)
-- Perspective: Receivables — aging vs a data-derived as-of date
--           (MAX order_date in the order book), deterministic
-- ============================================================
-- Query: Open Order Backlog Aging
-- Binding: gt_open_order_backlog_aging_20260706_185147
-- Description: How old is the open order backlog? Open orders with value and days since booking, aged against a data-derived as-of date.
WITH as_of AS (
    SELECT MAX(order_date) AS as_of_date FROM customer_order
)
SELECT
    co.order_id,
    co.customer_name,
    co.order_date,
    CAST(julianday(a.as_of_date) - julianday(co.order_date) AS INTEGER)
                                                                AS days_open,
    CASE
        WHEN julianday(a.as_of_date) - julianday(co.order_date) <= 30  THEN '0-30 days'
        WHEN julianday(a.as_of_date) - julianday(co.order_date) <= 90  THEN '31-90 days'
        WHEN julianday(a.as_of_date) - julianday(co.order_date) <= 180 THEN '91-180 days'
        ELSE 'Over 180 days'
    END                                                         AS age_bucket,
    ROUND(SUM(col.order_qty * col.unit_price), 2)               AS order_value
FROM customer_order co
JOIN customer_order_line col
    ON col.order_id = co.order_id
CROSS JOIN as_of a
WHERE co.status = 'Open'
  AND (:start_date IS NULL OR co.order_date >= :start_date)
GROUP BY co.order_id, co.customer_name, co.order_date, a.as_of_date
ORDER BY days_open DESC;
