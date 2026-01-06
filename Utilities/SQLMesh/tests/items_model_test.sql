-- name: items_model_has_rows
-- description: Simple smoke test ensuring `items_model` returns rows.
SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS success
FROM {{ ref('items_model') }};
