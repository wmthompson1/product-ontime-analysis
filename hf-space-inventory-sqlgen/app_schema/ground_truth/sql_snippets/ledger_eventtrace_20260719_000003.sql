-- Governed ledger query: chronological event trace for a job.
-- Every gl_events posting for the job in event order, with the originating
-- source document (table + row key) for a full audit trail.
-- Params: :job_id (optional work_order.wo_id — NULL traces all jobs),
--         :start_date / :end_date (optional ISO date bounds on event_date)
SELECT
    ge.event_id                         AS event_id,
    ge.job_id                           AS job_id,
    ge.event_type                       AS event_type,
    ROUND(ge.amount, 2)                 AS amount,
    ge.event_date                       AS event_date,
    ge.source_table                     AS source_table,
    ge.source_id                        AS source_id
FROM gl_events ge
WHERE (:job_id IS NULL OR ge.job_id = :job_id)
  AND (:start_date IS NULL OR ge.event_date >= :start_date)
  AND (:end_date IS NULL OR ge.event_date <= :end_date)
ORDER BY ge.event_date, ge.event_id;
