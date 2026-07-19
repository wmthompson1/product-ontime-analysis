-- Governed ledger query: finished goods produced over a period.
-- FG_COMPLETION postings in gl_finished_goods_inventory are signed positive
-- (value arriving into the Finished Goods bucket from WIP).
-- Params: :start_date / :end_date (optional ISO date bounds on event_date)
SELECT
    fg.part_id                          AS part_id,
    fg.job_id                           AS job_id,
    COUNT(*)                            AS completion_count,
    ROUND(SUM(fg.amount), 2)            AS finished_goods_value,
    MIN(fg.event_date)                  AS first_completion_date,
    MAX(fg.event_date)                  AS last_completion_date
FROM gl_finished_goods_inventory fg
WHERE fg.event_type = 'FG_COMPLETION'
  AND (:start_date IS NULL OR fg.event_date >= :start_date)
  AND (:end_date IS NULL OR fg.event_date <= :end_date)
GROUP BY fg.part_id, fg.job_id
ORDER BY finished_goods_value DESC, fg.part_id, fg.job_id;
