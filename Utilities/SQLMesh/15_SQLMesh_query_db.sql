-- ============================================================================
-- SQLMesh Physical Layer Query Examples
-- ============================================================================
-- These queries demonstrate how to query the physical tables created by SQLMesh
-- in the DuckDB database (db.db).
--
-- IMPORTANT: Tables must be backfilled before querying!
--   Run: sqlmesh plan
--   Then: Type 'y' to apply and backfill the data
--
-- You can run these queries with:
--   sqlmesh fetchdf "SELECT ..."
-- ============================================================================

-- Query 1: Raw Schema Nodes
-- Lists all database tables/entities from the schema metadata (seed layer)
-- ============================================================================
SELECT 
    node_id,
    concept_id,
    label,
    created_at
FROM raw__dev.schema_nodes
ORDER BY node_id
LIMIT 10;


-- Query 2: Staging Schema Nodes (Transformed)
-- Shows transformed schema nodes with mapped column names
-- ============================================================================
SELECT 
    table_name,
    table_type,
    description,
    created_at
FROM staging__dev.stg_schema_nodes
ORDER BY table_name
LIMIT 10;


-- Query 3: Schema Graph - Table Relationships
-- Demonstrates table relationships from schema edges (seed layer)
-- ============================================================================
SELECT 
    e.edge_id,
    e.from_node AS source_node,
    e.to_node AS target_node,
    e.relation AS relationship_type,
    e.created_at
FROM raw__dev.schema_edges AS e
ORDER BY e.edge_id
LIMIT 15;


-- ============================================================================
-- Usage Instructions:
-- ============================================================================
-- 1. First, backfill the tables:
--    sqlmesh plan
--    (type 'y' when prompted)
--
-- 2. Then run queries:
--    sqlmesh fetchdf "SELECT node_id, label FROM raw__dev.schema_nodes LIMIT 5"
--    sqlmesh fetchdf "SELECT * FROM staging__dev.stg_schema_nodes LIMIT 5"
--    sqlmesh fetchdf "SELECT * FROM raw__dev.schema_edges LIMIT 5"
--
-- 3. Or use Python:
--    from sqlmesh import Context
--    context = Context(paths=".")
--    df = context.fetchdf("SELECT * FROM raw__dev.schema_nodes LIMIT 5")
--    print(df)
--
-- Note: Physical schemas use __dev suffix in development environment
--       In production, tables are in 'raw' and 'staging' schemas
-- ============================================================================
