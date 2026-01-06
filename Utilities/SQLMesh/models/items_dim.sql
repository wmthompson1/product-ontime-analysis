-- name: items_dim
-- description: Dimension model for items built from `items_model`.
SELECT
  id AS item_id,
  name AS item_name
FROM {{ ref('items_model') }};
