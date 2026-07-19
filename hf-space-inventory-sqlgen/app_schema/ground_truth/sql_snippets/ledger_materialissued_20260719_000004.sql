-- Governed ledger query: material issued over a period.
-- RM_ISSUE postings in gl_raw_materials_inventory are signed negative
-- (value leaving the Raw Materials bucket into WIP); issued value is
-- reported as the positive magnitude.
-- Params: :start_date / :end_date (optional ISO date bounds on event_date)
SELECT
    rm.part_id                          AS part_id,
    rm.job_id                           AS job_id,
    COUNT(*)                            AS issue_count,
    ROUND(SUM(-rm.amount), 2)           AS material_value_issued,
    MIN(rm.event_date)                  AS first_issue_date,
    MAX(rm.event_date)                  AS last_issue_date
FROM gl_raw_materials_inventory rm
WHERE rm.event_type = 'RM_ISSUE'
  AND (:start_date IS NULL OR rm.event_date >= :start_date)
  AND (:end_date IS NULL OR rm.event_date <= :end_date)
GROUP BY rm.part_id, rm.job_id
ORDER BY material_value_issued DESC, rm.part_id, rm.job_id;
