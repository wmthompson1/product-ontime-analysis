/*
Inventory transaction reconciliation review — SQLite SYNTHETIC counterpart.

This is the SQLite-runnable synthetic version of the ground-truth T-SQL benchmark
in the same folder (Inventory_-_Transactions_AI_Review.sql). The reconciliation
logic — trace lot rollup vs. inventory ledger net effect vs. planning on-hand,
with a Y/N reconciled flag — is preserved exactly; only the dialect and the table
/ column names change to the local manufacturing.db ERP stand-in.

Ground-truth (Live.dbo.*, T-SQL)   ->  stand-in (manufacturing.db, SQLite)
  TRACE_INV_TRANS                   ->  trace_inventory_trace
  INVENTORY_TRANS                   ->  inventory_transaction
  PART_LOCATION                     ->  part_location          (added by migration)
  WAREHOUSE                         ->  warehouse              (added by migration)
  PART                              ->  part
  .qty / .transaction_date          ->  .quantity / .trans_date  (inventory_transaction)
  warehouse .id                     ->  warehouse .warehouse_id

warehouse + part_location are created and grounded by
hf-space-inventory-sqlgen/migrations/add_warehouse_part_location.py (on-hand per
part/site = the ledger net effect, so the on-hand axis reconciles with the ledger).

Parameters: this run targets part P-10011 at site SITE-1, which reconciles fully
(ledger 62 = on-hand 62 = trace 62 -> 'Y'). Swap the two literals below to explore
other cases, e.g. P-10010 / SITE-1 yields 'N' (on-hand matches the ledger but the
trace rollup differs).

Part-master columns the stand-in `part` table does NOT model
(mrp_required, fabricated, purchased, stocked, mrp_exceptions) are omitted; the
modeled analogs are mapped: description->part_description, status<-active,
stock_um<-unit_of_measure, commodity_code<-part_class.
*/

WITH trace_inv_trans AS (
    SELECT
        x.qty,
        t.transaction_id,
        t.trans_date            AS transaction_date,
        t.type                  AS transaction_type,
        t.class                 AS transaction_class,
        x.part_id,
        x.trace_id
    FROM trace_inventory_trace x
    JOIN inventory_transaction t
        ON x.transaction_id = t.transaction_id
    WHERE x.part_id = 'P-10011'
      AND t.site_id = 'SITE-1'
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
        t.trans_date            AS transaction_date,
        t.class                 AS transaction_class,
        t.type                  AS transaction_type,
        t.quantity              AS qty,
        CASE
            WHEN t.type = 'I' THEN t.quantity
            ELSE t.quantity * -1
        END AS effect_on_qty_on_hand
    FROM inventory_transaction t
    WHERE t.part_id = 'P-10011'
      AND t.site_id = 'SITE-1'
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
    FROM part_location pl
    JOIN warehouse w ON pl.warehouse_id = w.warehouse_id
    WHERE pl.part_id = 'P-10011'
      AND w.site_id = 'SITE-1'
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
    p.part_description AS description,
    f.ix_qty AS inv_xactn,
    f.oh_qty AS on_hand,
    f.tx_qty AS trace_xactn,
    f.is_reconciled,
    CASE WHEN p.active = 1 THEN 'Active' ELSE 'Obsolete' END AS status,
    p.unit_of_measure AS stock_um,
    p.part_class      AS commodity_code
FROM final_recon f
JOIN part p
    ON f.part_id = p.part_id
