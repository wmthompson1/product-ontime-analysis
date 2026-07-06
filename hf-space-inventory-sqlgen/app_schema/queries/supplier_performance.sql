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
-- Query: Supplier Scorecard
-- Description: Which suppliers are meeting delivery and quality thresholds? Delivery counts, on-time %, quality score, and late-rate penalty signal per supplier.
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
-- Query: Supplier Cost Penalties
-- Description: What penalty credits are owed for late deliveries? Estimated penalty credit per supplier (2% of delivery value per late event).
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
-- Query: Supplier Payables Exposure
-- Description: What is our total AP exposure by supplier for a period? Invoice counts, units received, estimated AP exposure, and payment recommendation.
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

-- ============================================================
-- Query 4 — supplier_payables_exposure (total due)
-- Intent:   What is our AP exposure by supplier? (exposure = total due)
-- Typical:  "What do we owe each supplier right now?"
--           "Total AP due by vendor"
-- Params:   :supplier_id (optional)
-- Perspective: Payables — exposure defined as TOTAL DUE: the sum of all
--           unpaid (Open or Disputed) invoice amounts from the payables
--           ledger. No estimates or cost proxies.
-- ============================================================
-- Query: Supplier AP Total Due
-- Description: What is our AP exposure by supplier, defined as total due — the sum of all unpaid (Open or Disputed) invoice amounts, with overdue split.
SELECT
    s.supplier_id,
    s.supplier_name,
    COUNT(p.invoice_id)                                         AS open_invoices,
    ROUND(SUM(p.amount_dollars), 2)                             AS total_due,
    ROUND(SUM(CASE WHEN p.status = 'Disputed'
                   THEN p.amount_dollars ELSE 0 END), 2)        AS disputed_amount,
    ROUND(SUM(CASE WHEN p.due_date <
                        (SELECT MAX(invoice_date) FROM payables)
                   THEN p.amount_dollars ELSE 0 END), 2)        AS overdue_amount,
    MIN(p.due_date)                                             AS earliest_due,
    MAX(p.due_date)                                             AS latest_due
FROM suppliers s
JOIN payables p
    ON p.supplier_id = s.supplier_id
WHERE p.status IN ('Open', 'Disputed')
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
GROUP BY s.supplier_id, s.supplier_name
ORDER BY total_due DESC;

-- ============================================================
-- Query 5 — supplier_payables_exposure (aging)
-- Intent:   How old is our unpaid AP, bucketed by days past due?
-- Typical:  "AP aging report by supplier"
--           "Which invoices are 90+ days past due?"
-- Params:   :supplier_id (optional)
-- Perspective: Payables — aging is computed against a data-derived
--           as-of date (MAX invoice_date in the ledger), so the report
--           is deterministic and never depends on the wall clock.
-- ============================================================
-- Query: AP Aging by Supplier
-- Description: How old is our unpaid AP? Unpaid (Open or Disputed) amounts bucketed by days past due — current, 1-30, 31-60, 61-90, and 90+ — per supplier.
WITH as_of AS (
    SELECT MAX(invoice_date) AS as_of_date FROM payables
)
SELECT
    s.supplier_id,
    s.supplier_name,
    ROUND(SUM(CASE WHEN p.due_date >= a.as_of_date
                   THEN p.amount_dollars ELSE 0 END), 2)        AS current_not_due,
    ROUND(SUM(CASE WHEN julianday(a.as_of_date) - julianday(p.due_date)
                        BETWEEN 1 AND 30
                   THEN p.amount_dollars ELSE 0 END), 2)        AS past_due_1_30,
    ROUND(SUM(CASE WHEN julianday(a.as_of_date) - julianday(p.due_date)
                        BETWEEN 31 AND 60
                   THEN p.amount_dollars ELSE 0 END), 2)        AS past_due_31_60,
    ROUND(SUM(CASE WHEN julianday(a.as_of_date) - julianday(p.due_date)
                        BETWEEN 61 AND 90
                   THEN p.amount_dollars ELSE 0 END), 2)        AS past_due_61_90,
    ROUND(SUM(CASE WHEN julianday(a.as_of_date) - julianday(p.due_date) > 90
                   THEN p.amount_dollars ELSE 0 END), 2)        AS past_due_over_90,
    ROUND(SUM(p.amount_dollars), 2)                             AS total_due
FROM suppliers s
JOIN payables p
    ON p.supplier_id = s.supplier_id
CROSS JOIN as_of a
WHERE p.status IN ('Open', 'Disputed')
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
GROUP BY s.supplier_id, s.supplier_name
ORDER BY past_due_over_90 DESC, total_due DESC;

-- ============================================================
-- Query 6 — supplier_payables_exposure (match exceptions)
-- Intent:   Which unpaid invoices failed three-way match?
-- Typical:  "Show invoices on match exception hold"
--           "What AP is blocked by three-way match failures?"
-- Params:   :supplier_id (optional)
-- Perspective: Payables — unpaid invoices whose three_way_match_status
--           is Exception (PO / receipt / invoice disagree). These should
--           be held from payment until resolved.
-- ============================================================
-- Query: Three-Way Match Exceptions
-- Description: Which unpaid invoices failed three-way match? Exception-status invoices per supplier with amounts at risk and the linked PO.
SELECT
    s.supplier_id,
    s.supplier_name,
    p.invoice_number,
    p.po_id,
    p.invoice_date,
    p.due_date,
    ROUND(p.amount_dollars, 2)                                  AS amount_on_hold,
    p.status                                                    AS invoice_status
FROM payables p
JOIN suppliers s
    ON s.supplier_id = p.supplier_id
WHERE p.three_way_match_status = 'Exception'
  AND p.status IN ('Open', 'Disputed')
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
ORDER BY p.amount_dollars DESC;
