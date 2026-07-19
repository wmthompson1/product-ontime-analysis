-- Ground Truth SQL: Job Costing Ledger (gl_*) Queries
-- Perspective: General_Ledger
-- Category: job_costing_ledger
-- Source: Manufacturing SQL Semantic Layer (Replit public repo)
--
-- NOTE ON FRAMING: the gl_* tables are the deterministic job-costing ledger
-- backfilled from the manufacturing documents (material_issue, labor_ticket,
-- receiving, work_order completions). Every posting is data-derived — dates
-- come from the source document, never the wall clock. Bucket amounts are
-- signed: value entering a bucket is positive, value leaving it is negative.
--
-- Temporal binding keys: :as_of_date / :start_date / :end_date (ISO dates,
-- optional event_date bounds), :job_id (optional work_order.wo_id filter).

-- ============================================================
-- Query 1 — ledger_inventory_balance
-- Intent:   What is the balance of each inventory bucket?
-- Typical:  "Show inventory balances by bucket"
--           "How much value sits in raw materials, WIP, and finished goods?"
-- Params:   :as_of_date (optional)
-- Perspective: General_Ledger — perpetual bucket balances from the sub-ledgers
-- ============================================================
-- Query: Inventory Balance per Bucket
-- Description: Signed running balance of the Raw Materials, Work in Process, and Finished Goods buckets from the gl_* sub-ledgers, optionally as of a cutoff date.
SELECT
    1                                   AS bucket_order,
    'Raw Materials'                     AS inventory_bucket,
    COUNT(*)                            AS posting_count,
    ROUND(SUM(amount), 2)               AS balance
FROM gl_raw_materials_inventory
WHERE (:as_of_date IS NULL OR event_date <= :as_of_date)
UNION ALL
SELECT
    2,
    'Work in Process',
    COUNT(*),
    ROUND(SUM(amount), 2)
FROM gl_wip_inventory
WHERE (:as_of_date IS NULL OR event_date <= :as_of_date)
UNION ALL
SELECT
    3,
    'Finished Goods',
    COUNT(*),
    ROUND(SUM(amount), 2)
FROM gl_finished_goods_inventory
WHERE (:as_of_date IS NULL OR event_date <= :as_of_date)
ORDER BY bucket_order;

-- ============================================================
-- Query 2 — ledger_job_cost_summary
-- Intent:   What has each job cost, by cost element?
-- Typical:  "Job cost summary for WO-00004"
--           "Show WIP for job 42"
-- Params:   :job_id, :start_date, :end_date (all optional)
-- Perspective: General_Ledger — cost roll-up per work order and element
-- ============================================================
-- Query: Job Cost Summary by Cost Element
-- Description: What has each job cost? gl_job_cost_detail rolled up per work order and cost element (LABOR / MATERIAL / BURDEN / SERVICE), optionally filtered to one job and/or a posting window.
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

-- ============================================================
-- Query 3 — ledger_event_trace
-- Intent:   What happened on this job, in order?
-- Typical:  "Trace the ledger events for WO-00006"
--           "Show the event trace for job WO-00001"
-- Params:   :job_id, :start_date, :end_date (all optional)
-- Perspective: General_Ledger — chronological audit trail with source docs
-- ============================================================
-- Query: Job Event Trace
-- Description: Chronological gl_events audit trail for a job — every posting in event order with the originating source document (table + row key).
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

-- ============================================================
-- Query 4 — ledger_material_issued
-- Intent:   What material was issued over a period?
-- Typical:  "What material was issued in July?"
--           "Material issued to jobs last quarter"
-- Params:   :start_date, :end_date (both optional)
-- Perspective: General_Ledger — RM_ISSUE outflow from the RM bucket
-- ============================================================
-- Query: Material Issued over a Period
-- Description: RM_ISSUE postings (signed negative out of the Raw Materials bucket) reported as positive issued value per part and job over an optional date window.
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

-- ============================================================
-- Query 5 — ledger_fg_production
-- Intent:   What finished goods were produced over a period?
-- Typical:  "What finished goods were produced this year?"
--           "FG completions by part in Q2"
-- Params:   :start_date, :end_date (both optional)
-- Perspective: General_Ledger — FG_COMPLETION inflow into the FG bucket
-- ============================================================
-- Query: Finished Goods Produced over a Period
-- Description: FG_COMPLETION postings (signed positive into the Finished Goods bucket) per part and job over an optional date window.
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
