-- Aggregate quantities per item (uses `items_dim`).
SELECT
    item_id,
    SUM(qty) AS total_qty
FROM {{ ref('items_dim') }}
GROUP BY item_id;