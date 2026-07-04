/*
ARCHIVED 2026-07-04 - perspective: manufacturing. Moved out of the knowledge
loop (was docs/my-mrp-kb/05-inventory-transactions/Inventory_-_Transactions_AI_Review.sql);
POC-era review query kept as ground-truth reference only. NOTE: this is the
real-source T-SQL benchmark (Live.dbo.*) - a faithful reference only, NOT
runnable against the synthetic SQLite manufacturing.db. Its runnable SQLite
counterpart is archived beside this file as
manufacturing_inventorytransactions_20260704_000005.sql.
*/

/*
Inventory transaction reconciliation review.

SQLMesh-friendly notes:
- keep the query read-only and CTE-based
- keep fully qualified ERP table names
- retain the multi-table transaction lineage across trace, transaction, part-location,
  warehouse, and part master tables
*/

WITH trace_inv_trans AS (
    SELECT
        x.qty,
        t.transaction_id,
        t.transaction_date,
        t.type AS transaction_type,
        t.class AS transaction_class,
        x.part_id,
        x.trace_id
    FROM Live.dbo.TRACE_INV_TRANS x
    JOIN Live.dbo.INVENTORY_TRANS t
        ON x.transaction_id = t.transaction_id
    WHERE x.part_id = '20240C-063'
      AND t.site_id = 'SK01'
),

tixact_agg_by_xact AS (
    SELECT
        part_id,
        transaction_id,
        SUM(qty) AS qty
    FROM trace_inv_trans
    GROUP BY part_id, transaction_id
),

inventory_trans_cte AS (
    SELECT
        t.part_id,
        t.transaction_id,
        t.transaction_date,
        t.class AS transaction_class,
        t.type AS transaction_type,
        t.qty,
        CASE 
            WHEN t.type = 'I' THEN t.qty
            ELSE t.qty * -1
        END AS effect_on_qty_on_hand
    FROM Live.dbo.INVENTORY_TRANS t
    WHERE t.part_id = '20240C-063'
      AND t.site_id = 'SK01'
),

results AS (
    SELECT
        ix.part_id,
        ix.transaction_id,
        ix.effect_on_qty_on_hand,
        tx.qty
    FROM inventory_trans_cte ix
    LEFT JOIN tixact_agg_by_xact tx
        ON ix.transaction_id = tx.transaction_id
       AND ix.part_id = tx.part_id
),

results_agg AS (
    SELECT
        part_id,
        SUM(effect_on_qty_on_hand) AS effect_on_qty_on_hand,
        SUM(qty) AS qty
    FROM results
    GROUP BY part_id
),

planning_on_hand AS (
    SELECT
        pl.part_id,
        SUM(pl.qty) AS qty
    FROM Live.dbo.PART_LOCATION pl
    JOIN Live.dbo.WAREHOUSE w ON pl.warehouse_id = w.id
    WHERE pl.part_id = '20240C-063'
      AND w.site_id = 'SK01'
    GROUP BY pl.part_id
),

final_recon AS (
    SELECT
        r.part_id,
        r.qty AS tx_qty,
        oh.qty AS oh_qty,
        r.effect_on_qty_on_hand AS ix_qty,
        CASE 
            WHEN r.qty = oh.qty AND oh.qty = r.effect_on_qty_on_hand
            THEN 'Y'
            ELSE 'N'
        END AS is_reconciled
    FROM results_agg r
    JOIN planning_on_hand oh
        ON r.part_id = oh.part_id
),
count_of_transactions AS (
    SELECT
        part_id,
        COUNT(DISTINCT transaction_id) AS num_transactions
    FROM inventory_trans_cte
    GROUP BY part_id
)

SELECT
    f.part_id,
    p.description,
    f.ix_qty AS inv_xactn,
    f.oh_qty AS on_hand,
    f.tx_qty AS trace_xactn,
    f.is_reconciled,
    p.status,
    p.mrp_required,
    p.commodity_code,
    p.stock_um,
    p.fabricated,
    p.purchased,
    p.stocked,
    p.mrp_exceptions
FROM final_recon f
JOIN Live.dbo.PART p
    ON f.part_id = p.id
