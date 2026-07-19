-- Governed ledger query: job cost summary by job and cost element.
-- Rolls up gl_job_cost_detail (LABOR / MATERIAL / BURDEN / SERVICE lines)
-- per work order, optionally filtered to one job and/or a posting window.
-- Params: :job_id (optional work_order.wo_id),
--         :start_date / :end_date (optional ISO date bounds on event_date)
SELECT
    jcd.job_id                          AS job_id,
    jcd.event_type                      AS cost_element,
    COUNT(*)                            AS posting_count,
    ROUND(SUM(jcd.amount), 2)           AS total_cost
FROM gl_job_cost_detail jcd
WHERE (:job_id IS NULL OR jcd.job_id = :job_id)
  AND (:start_date IS NULL OR jcd.event_date >= :start_date)
  AND (:end_date IS NULL OR jcd.event_date <= :end_date)
GROUP BY jcd.job_id, jcd.event_type
ORDER BY jcd.job_id, jcd.event_type;
