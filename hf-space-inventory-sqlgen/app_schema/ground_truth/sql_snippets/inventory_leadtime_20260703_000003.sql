-- Lead Time Summary by Part Class
-- Aggregates replenishment lead time (days) across active parts, grouped by
-- sourcing class (MAKE vs BUY).  Supports MRP planning-horizon decisions and
-- capacity review meetings.
SELECT
    p.part_class,
    COUNT(*)                                   AS part_count,
    ROUND(AVG(p.lead_time_days), 1)            AS avg_lead_time_days,
    MIN(p.lead_time_days)                      AS min_lead_time_days,
    MAX(p.lead_time_days)                      AS max_lead_time_days,
    SUM(CASE WHEN p.lead_time_days > 90 THEN 1 ELSE 0 END) AS long_lead_count
FROM part p
WHERE p.active = 1
  AND p.lead_time_days > 0
GROUP BY p.part_class
ORDER BY avg_lead_time_days DESC
