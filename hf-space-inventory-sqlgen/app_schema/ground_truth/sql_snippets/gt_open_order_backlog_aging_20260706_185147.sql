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