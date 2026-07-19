-- Governed ledger query: inventory balance per bucket (RM / WIP / FG).
-- Signed, running balance of each perpetual inventory bucket from the
-- gl_* sub-ledgers, optionally as of a cutoff date.
-- Params: :as_of_date (optional ISO date upper bound on event_date)
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
