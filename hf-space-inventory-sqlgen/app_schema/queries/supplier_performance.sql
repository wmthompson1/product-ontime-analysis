-- Ground Truth SQL: Supplier / Payables Queries
-- Perspective: Payables · Quality
-- Category: supplier_performance
-- Source: Manufacturing SQL Semantic Layer (Replit public repo)
--
-- NOTE ON FRAMING: Supplier queries ARE payables queries.
-- The Finance/AP stakeholder drives most of these intents:
--   "Which suppliers owe us credits?" = supplier_cost_penalties (Finance)
--   "Which suppliers are at risk?"    = supplier_scorecard (Quality → also Finance)
--   "What is our AP exposure?"        = supplier_payables_exposure (Finance)
--
-- When the dispatcher hears "payables", "AP", "vendor invoice", or "owe",
-- it should route to this category before considering quality-only intents.
--
-- Temporal binding key: :start_date  (ISO date, e.g. '2025-07-01')
-- Supplier binding key: :supplier_id (integer, optional)

-- ============================================================
-- Query 1 — supplier_scorecard
-- Intent:   Which suppliers are meeting delivery and quality thresholds?
-- Typical:  "Supplier scorecard for the last 30 days"
--           "Which vendors are underperforming on quality?"
-- Params:   :start_date (delivery_date lower bound)
-- Perspectives: Quality (primary) · Finance (vendor payment-term decisions)
-- ============================================================
SELECT
    s.supplier_id,
    s.supplier_name,
    s.performance_rating,
    s.certification_level,
    COUNT(d.delivery_id)                                        AS total_deliveries,
    ROUND(AVG(d.ontime_rate) * 100, 1)                          AS avg_ontime_pct,
    ROUND(AVG(d.quality_score) * 100, 1)                        AS avg_quality_score,
    COUNT(CASE WHEN d.ontime_rate >= 0.95 THEN 1 END)           AS on_time_deliveries,
    COUNT(CASE WHEN d.ontime_rate < 0.80  THEN 1 END)           AS late_deliveries,
    -- AP signal: late delivery rate drives penalty credit calculation
    ROUND(
        CAST(COUNT(CASE WHEN d.ontime_rate < 0.80 THEN 1 END) AS REAL)
        / NULLIF(COUNT(d.delivery_id), 0) * 100, 1
    )                                                           AS late_rate_pct
FROM suppliers s
LEFT JOIN daily_deliveries d
    ON s.supplier_id = d.supplier_id
   AND d.delivery_date >= :start_date
GROUP BY s.supplier_id, s.supplier_name, s.performance_rating, s.certification_level
ORDER BY avg_ontime_pct ASC, avg_quality_score ASC;

-- ============================================================
-- Query 2 — supplier_cost_penalties
-- Intent:   What penalty credits are owed for late deliveries?
-- Typical:  "What penalties are owed for late deliveries since July 1st?"
--           "Calculate vendor penalty exposure from July"
-- Params:   :start_date
-- Perspective: Payables — this is the primary payables query
-- ============================================================
SELECT
    s.supplier_id,
    s.supplier_name,
    s.certification_level,
    COUNT(d.delivery_id)                                        AS total_deliveries,
    COUNT(CASE WHEN d.ontime_rate < 0.80 THEN 1 END)           AS late_deliveries,
    -- Penalty model: 2% of delivery value per late event (illustrative rate)
    ROUND(
        COUNT(CASE WHEN d.ontime_rate < 0.80 THEN 1 END)
        * d.actual_quantity * 0.02, 2
    )                                                           AS estimated_penalty_credit,
    ROUND(AVG(d.quality_score), 3)                              AS avg_quality,
    MIN(d.delivery_date)                                        AS earliest_delivery,
    MAX(d.delivery_date)                                        AS latest_delivery
FROM suppliers s
JOIN daily_deliveries d
    ON s.supplier_id = d.supplier_id
WHERE d.delivery_date >= :start_date
GROUP BY s.supplier_id, s.supplier_name, s.certification_level, d.actual_quantity
HAVING COUNT(CASE WHEN d.ontime_rate < 0.80 THEN 1 END) > 0
ORDER BY estimated_penalty_credit DESC;

-- ============================================================
-- Query 3 — supplier_payables_exposure
-- Intent:   What is our total AP exposure by supplier for a period?
-- Typical:  "Show me payables exposure by vendor from July 1st"
--           "What do we owe suppliers this quarter?"
-- Params:   :start_date, :supplier_id (optional)
-- Perspective: Payables — pure payables roll-up
-- Note:     unit_cost is sourced from product_lines.unit_price as a proxy
--           until a purchase_orders table is added to this schema.
-- ============================================================
SELECT
    s.supplier_id,
    s.supplier_name,
    s.certification_level,
    s.performance_rating,
    COUNT(d.delivery_id)                                        AS invoice_count,
    SUM(d.actual_quantity)                                      AS total_units_received,
    -- Cost proxy: actual_quantity × median unit_price from product_lines
    ROUND(
        SUM(d.actual_quantity) * (
            SELECT AVG(pl.unit_price) FROM product_lines pl
        ), 2
    )                                                           AS estimated_ap_exposure,
    -- Discount signal: high quality + on-time → eligible for early-pay discount
    CASE
        WHEN AVG(d.quality_score) >= 0.95
         AND AVG(d.ontime_rate)   >= 0.95 THEN 'Early-Pay Eligible'
        WHEN AVG(d.quality_score) >= 0.80 THEN 'Standard Terms'
        ELSE 'Hold — Review Required'
    END                                                         AS payment_recommendation,
    ROUND(AVG(d.ontime_rate) * 100, 1)                          AS avg_ontime_pct,
    ROUND(AVG(d.quality_score) * 100, 1)                        AS avg_quality_score
FROM suppliers s
JOIN daily_deliveries d
    ON s.supplier_id = d.supplier_id
WHERE d.delivery_date >= :start_date
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
GROUP BY s.supplier_id, s.supplier_name, s.certification_level, s.performance_rating
ORDER BY estimated_ap_exposure DESC;
