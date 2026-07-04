-- Available To Promise (ATP) by Part and Bucket — time-phased, set-aware
-- ATP is the cumulative Projected Available Balance (PAB): the running stock
-- position across the planning horizon = on-hand carried forward, plus firm
-- scheduled receipts, minus committed open-order demand, netted period by period.
-- One row per (part, bucket); atp_pab is the ATP available AS OF the end of that
-- bucket, so it answers "available to promise *by when*".
-- Set semantics (per docs/mrp_set_semantics_criteria.md §4.2 / §5):
--   * Demand:   ONLY customer_order.status = 'Open' lines (Closed / Shipped /
--               Cancelled orders are not live commitments).  Status comes from
--               the parent customer_order (the line has no status of its own).
--   * Supply:   on-hand + firm scheduled receipts = non-closed work orders
--               (unreleased / firmed / released) + open purchase orders
--               (status Open / Partial).  Closed / Received / Cancelled POs and
--               closed WOs are NOT future supply.
--   * Horizon:  data-derived AS_OF = MAX(work_order.close_date); PLAN_START =
--               first of that month; 6 monthly buckets M0..M5; anything dated
--               before PLAN_START folds into "Past Due" (never wall-clock).
-- Mirrors the PAB row that mrp_engine.compute_mrp_grid produces per part.
WITH h AS (
    SELECT date(COALESCE((SELECT MAX(close_date) FROM work_order), '2026-06-12'),
                'start of month') AS plan_start
),
buckets(idx, label, b_start, b_end) AS (
    SELECT -1, 'Past Due', '0001-01-01', (SELECT plan_start FROM h)
    UNION ALL
    SELECT idx + 1, 'M' || CAST(idx + 1 AS TEXT), b_end, date(b_end, '+1 month')
    FROM buckets
    WHERE idx < 5
),
demand AS (
    SELECT col.part_id, b.idx AS idx, SUM(col.order_qty) AS qty
    FROM customer_order_line col
    JOIN customer_order o ON o.order_id = col.order_id
    JOIN buckets b
      ON col.need_by_date IS NOT NULL
     AND date(col.need_by_date) >= b.b_start
     AND date(col.need_by_date) <  b.b_end
    WHERE o.status = 'Open'
    GROUP BY col.part_id, b.idx
),
receipts AS (
    SELECT part_id, idx, SUM(qty) AS qty
    FROM (
        SELECT wo.part_id AS part_id, b.idx AS idx, wo.quantity AS qty
        FROM work_order wo
        JOIN buckets b
          ON wo.required_date IS NOT NULL
         AND date(wo.required_date) >= b.b_start
         AND date(wo.required_date) <  b.b_end
        WHERE wo.status IN ('unreleased', 'firmed', 'released')
        UNION ALL
        SELECT pl.part_id AS part_id, b.idx AS idx, pl.quantity AS qty
        FROM po_line pl
        JOIN purchase_order po ON po.po_id = pl.po_id
        JOIN buckets b
          ON po.required_date IS NOT NULL
         AND date(po.required_date) >= b.b_start
         AND date(po.required_date) <  b.b_end
        WHERE po.status IN ('Open', 'Partial')
    )
    GROUP BY part_id, idx
)
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    b.idx                                   AS bucket_index,
    b.label                                 AS bucket,
    b.b_start                               AS bucket_start,
    p.on_hand_qty,
    COALESCE(d.qty, 0)                      AS gross_requirements,
    COALESCE(r.qty, 0)                      AS scheduled_receipts,
    ROUND(
        p.on_hand_qty
        + SUM(COALESCE(r.qty, 0) - COALESCE(d.qty, 0)) OVER (
            PARTITION BY p.part_id ORDER BY b.idx
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ),
        2
    )                                       AS atp_pab,
    CASE
        WHEN p.on_hand_qty
             + SUM(COALESCE(r.qty, 0) - COALESCE(d.qty, 0)) OVER (
                 PARTITION BY p.part_id ORDER BY b.idx
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) >= 0
        THEN 'AVAILABLE'
        ELSE 'SHORT'
    END                                     AS atp_status
FROM part p
CROSS JOIN buckets b
LEFT JOIN demand   d ON d.part_id = p.part_id AND d.idx = b.idx
LEFT JOIN receipts r ON r.part_id = p.part_id AND r.idx = b.idx
WHERE p.active = 1
ORDER BY p.part_id, b.idx
