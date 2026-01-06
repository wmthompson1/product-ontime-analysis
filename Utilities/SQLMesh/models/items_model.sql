MODEL (
  name items_model,
  kind FULL,
  dialect duckdb
);

-- Simple test model that creates sample data
SELECT 
  1 AS id,
  'test_item' AS name,
  10 AS qty
UNION ALL
SELECT 
  2 AS id,
  'another_item' AS name,
  20 AS qty;
