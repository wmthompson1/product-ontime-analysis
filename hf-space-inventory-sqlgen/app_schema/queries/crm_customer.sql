-- Ground Truth SQL: CRM Customer Queries
-- Perspective: Receivables · CRM
-- Category: crm
-- Source: Manufacturing SQL Semantic Layer (Replit public repo)
--
-- These queries cover the CRM surface: customer master, address resolution,
-- and revenue aggregation. The CRM_Join intent (customer → customer_address
-- via customer_id FK) is the structural foundation; semantic intents layer on
-- top to route dispatcher questions to the right query.
--
-- Temporal binding key: :start_date  (ISO date, e.g. '2025-07-01')
-- Identity binding key: :customer_id (integer, optional — omit for full set)
-- Location binding key: :city / :state (optional filters on address)

-- ============================================================
-- Query 1 — crm_customer_profile
-- Intent:   Who is this customer and where do we ship to?
-- Typical:  "Show me the customer profile for account 42"
--           "Pull contact details with shipping address"
-- Params:   :customer_id (optional — omit to return all active customers)
-- Joins:    customer ←→ customer_address  (the CRM_Join structural edge)
-- ============================================================
SELECT
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.created_at                         AS customer_since,
    a.address_id,
    a.street,
    a.city,
    a.state,
    a.zip,
    -- Full display fields for UI / agent output
    (c.first_name || ' ' || c.last_name) AS full_name,
    (a.street || ', ' || a.city || ', ' || a.state || ' ' || COALESCE(a.zip, ''))
                                         AS shipping_address
FROM customer c
LEFT JOIN customer_address a
    ON a.customer_id = c.customer_id
WHERE (:customer_id IS NULL OR c.customer_id = :customer_id)
ORDER BY c.last_name, c.first_name, a.address_id;

-- ============================================================
-- Query 2 — crm_customer_revenue
-- Intent:   What is the revenue per customer for a date range?
-- Typical:  "Show me revenue by customer from July 1st"
--           "Which customers drove the most sales this quarter?"
-- Params:   :start_date (sale_date lower bound)
-- Joins:    customer ←→ sales  (revenue roll-up with address enrichment)
-- ============================================================
SELECT
    c.customer_id,
    (c.first_name || ' ' || c.last_name)  AS full_name,
    c.email,
    a.city,
    a.state,
    COUNT(s.sale_id)                       AS total_orders,
    ROUND(SUM(s.amount_dollars), 2)        AS total_revenue,
    ROUND(AVG(s.amount_dollars), 2)        AS avg_order_value,
    MIN(s.sale_date)                       AS first_order,
    MAX(s.sale_date)                       AS last_order,
    -- Product mix — null if product_line not populated (legacy records)
    GROUP_CONCAT(DISTINCT s.product_line)  AS product_lines_purchased
FROM customer c
LEFT JOIN customer_address a
    ON a.customer_id = c.customer_id
JOIN sales s
    ON s.customer_id = c.customer_id
WHERE s.sale_date >= :start_date
GROUP BY c.customer_id, c.first_name, c.last_name, c.email, a.city, a.state
ORDER BY total_revenue DESC;

-- ============================================================
-- Query 3 — crm_customer_address_lookup
-- Intent:   Find customers by region or city for territory planning
-- Typical:  "Which customers are in California?"
--           "Show me all ship-to addresses in the Southwest"
-- Params:   :city (optional), :state (optional)
-- Joins:    customer_address → customer  (address-first lookup)
-- ============================================================
SELECT
    a.state,
    a.city,
    a.zip,
    COUNT(DISTINCT a.customer_id)          AS customer_count,
    GROUP_CONCAT(
        c.first_name || ' ' || c.last_name,
        ' | '
    )                                      AS customer_names,
    GROUP_CONCAT(c.email, ' | ')           AS emails
FROM customer_address a
JOIN customer c
    ON c.customer_id = a.customer_id
WHERE (:state IS NULL OR a.state = :state)
  AND (:city  IS NULL OR a.city  = :city)
GROUP BY a.state, a.city, a.zip
ORDER BY a.state, a.city;
