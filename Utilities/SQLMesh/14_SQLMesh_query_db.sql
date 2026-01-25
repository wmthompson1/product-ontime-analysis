-- SQLMesh Query Reference for db.db
-- Use with: sqlite3 db.db < 14_SQLMesh_query_db.sql
-- Or open in any SQLite browser and run individual queries

-- ============================================================
-- RAW LAYER TABLES
-- ============================================================

-- Corrective Actions (NCM remediation records)
SELECT * FROM raw.corrective_actions;

-- Inspections (quality inspection records)
-- SELECT * FROM raw.inspections;

-- Non-Conformance Materials (NCM defect records)
-- SELECT * FROM raw.non_conformance_materials;

-- Parts (manufactured components)
-- SELECT * FROM raw.parts;

-- Production Orders (manufacturing work orders)
-- SELECT * FROM raw.production_orders;

-- Suppliers (vendor/supplier master)
-- SELECT * FROM raw.suppliers;

-- Work Centers (production stations)
-- SELECT * FROM raw.work_centers;

-- ============================================================
-- STAGING LAYER TABLES
-- ============================================================

-- Staged Corrective Actions
-- SELECT * FROM staging.stg_corrective_actions;

-- Staged Inspections
-- SELECT * FROM staging.stg_inspections;

-- Staged NCM Records
-- SELECT * FROM staging.stg_non_conformance_materials;

-- Staged Parts
-- SELECT * FROM staging.stg_parts;

-- Staged Production Orders
-- SELECT * FROM staging.stg_production_orders;

-- Staged Suppliers
-- SELECT * FROM staging.stg_suppliers;

-- Staged Work Centers
-- SELECT * FROM staging.stg_work_centers;

-- ============================================================
-- SCHEMA METADATA TABLES (Graph Constructs)
-- ============================================================

-- Schema Nodes (tables/fields in graph)
-- SELECT * FROM staging.stg_schema_nodes;

-- Schema Edges (relationships between nodes)
-- SELECT * FROM staging.stg_schema_edges;

-- Schema Concepts (semantic concepts like "defect", "part")
-- SELECT * FROM staging.stg_schema_concepts;

-- Concept-Field Mappings (which fields map to which concepts)
-- SELECT * FROM staging.stg_schema_concept_fields;

-- ============================================================
-- USEFUL ANALYTICAL QUERIES
-- ============================================================

-- Count records per raw table
-- SELECT 'corrective_actions' AS table_name, COUNT(*) AS row_count FROM raw.corrective_actions
-- UNION ALL SELECT 'inspections', COUNT(*) FROM raw.inspections
-- UNION ALL SELECT 'non_conformance_materials', COUNT(*) FROM raw.non_conformance_materials
-- UNION ALL SELECT 'parts', COUNT(*) FROM raw.parts
-- UNION ALL SELECT 'production_orders', COUNT(*) FROM raw.production_orders
-- UNION ALL SELECT 'suppliers', COUNT(*) FROM raw.suppliers
-- UNION ALL SELECT 'work_centers', COUNT(*) FROM raw.work_centers;

-- List all concepts and their field mappings
-- SELECT c.concept_name, cf.field_name
-- FROM staging.stg_schema_concepts c
-- JOIN staging.stg_schema_concept_fields cf ON c.id = cf.concept_id
-- ORDER BY c.concept_name;

-- Find nodes by type (table vs field)
-- SELECT node_type, COUNT(*) FROM staging.stg_schema_nodes GROUP BY node_type;

-- List all edges (relationships) in schema graph
-- SELECT source_id, edge_type, target_id FROM staging.stg_schema_edges;
