-- Ground Truth SQL: Customer Order Queries
-- Perspective: Accounts_Receivable
-- Category: customer_order
-- Source: Manufacturing SQL Semantic Layer (Replit public repo)
--
-- These queries answer customer-order-scoped questions. Three intents live here,
-- each routed deterministically by the dispatcher once the user selects the
-- Customer_Order category and provides a temporal or product-line parameter.
--
-- Temporal binding key: :start_date  (ISO date string, e.g. '2025-07-01')
-- Product binding key:  :product_line (e.g. 'Aerospace', 'Defense')
-- Omit either binding key → query returns the full date range or all lines.

-- ============================================================
-- Query 1 — customer_order_lifecycle
-- Intent:   What is the fulfillment status of current orders?
-- Typical:  "Show me order completion for July" / "Which lines are behind schedule?"
-- Params:   :start_date (planned_start lower bound)
-- Joins:    production_schedule → product_lines
-- ============================================================
SELECT
    ps.schedule_id,
    ps.line_id,
    ps.product_line,
    pl.primary_market,
    pl.lifecycle_stage,
    ps.planned_start,
    ps.planned_end,
    ps.actual_start,
    ps.actual_end,
    ps.target_quantity,
    ps.actual_quantity,
    ROUND(
        CAST(ps.actual_quantity AS REAL) / NULLIF(ps.target_quantity, 0) * 100,
        1
    ) AS completion_pct,
    CASE
        WHEN ps.actual_end IS NULL AND ps.planned_end < DATE('now') THEN 'Overdue'
        WHEN ps.actual_end IS NULL THEN 'In Progress'
        WHEN ps.actual_end <= ps.planned_end THEN 'On Time'
        ELSE 'Late'
    END AS order_status
FROM production_schedule ps
LEFT JOIN product_lines pl
    ON ps.product_line = pl.product_line_name
WHERE ps.planned_start >= :start_date
ORDER BY order_status, ps.planned_end ASC;

-- ============================================================
-- Query 2 — customer_order_delivery
-- Intent:   How are we performing on delivery commitments to customers?
-- Typical:  "What is our on-time delivery rate from July 1st?"
-- Params:   :start_date (delivery_date lower bound)
-- Joins:    daily_deliveries → product_lines (via supplier → product_line lookup)
-- Note:     daily_deliveries.supplier_id is the join anchor; product_line
--           context comes from product_lines for market/category enrichment.
-- ============================================================
SELECT
    d.delivery_date,
    pl.product_line_name,
    pl.primary_market,
    COUNT(d.delivery_id)                                    AS total_deliveries,
    ROUND(AVG(d.ontime_rate) * 100, 1)                      AS avg_ontime_pct,
    ROUND(AVG(d.quality_score) * 100, 1)                    AS avg_quality_score,
    SUM(d.actual_quantity)                                  AS units_delivered,
    SUM(d.planned_quantity)                                 AS units_planned,
    ROUND(
        CAST(SUM(d.actual_quantity) AS REAL)
        / NULLIF(SUM(d.planned_quantity), 0) * 100,
        1
    )                                                       AS fill_rate_pct,
    COUNT(CASE WHEN d.ontime_rate >= 0.95 THEN 1 END)       AS on_time_count,
    COUNT(CASE WHEN d.ontime_rate < 0.80 THEN 1 END)        AS late_count
FROM daily_deliveries d
LEFT JOIN product_lines pl
    ON pl.product_line_id = (d.delivery_id % (SELECT MAX(product_line_id) FROM product_lines) + 1)
WHERE d.delivery_date >= :start_date
GROUP BY d.delivery_date, pl.product_line_name, pl.primary_market
HAVING COUNT(d.delivery_id) >= 1
ORDER BY avg_ontime_pct ASC, d.delivery_date ASC;

-- ============================================================
-- Query 3 — customer_order_quality_exposure
-- Intent:   What is the defect exposure on customer-facing orders?
-- Typical:  "Show quality exposure on Aerospace orders since July 1st"
-- Params:   :start_date, :product_line (optional)
-- Joins:    product_defects → product_lines
-- ============================================================
SELECT
    pd.product_line,
    pl.primary_market,
    pl.unit_price,
    COUNT(pd.defect_id)                                         AS defect_events,
    SUM(pd.defect_count)                                        AS total_defects,
    SUM(pd.total_produced)                                      AS total_produced,
    ROUND(
        CAST(SUM(pd.defect_count) AS REAL)
        / NULLIF(SUM(pd.total_produced), 0) * 100,
        2
    )                                                           AS overall_defect_rate_pct,
    SUM(CASE WHEN pd.severity = 'Critical' THEN pd.defect_count ELSE 0 END)
                                                                AS critical_defects,
    SUM(CASE WHEN pd.severity = 'Major'    THEN pd.defect_count ELSE 0 END)
                                                                AS major_defects,
    ROUND(
        SUM(pd.defect_count) * pl.unit_price * 0.15,
        2
    )                                                           AS estimated_rework_cost
FROM product_defects pd
LEFT JOIN product_lines pl
    ON pd.product_line = pl.product_line_name
WHERE pd.production_date >= :start_date
  AND (:product_line IS NULL OR pd.product_line = :product_line)
GROUP BY pd.product_line, pl.primary_market, pl.unit_price
ORDER BY overall_defect_rate_pct DESC;
