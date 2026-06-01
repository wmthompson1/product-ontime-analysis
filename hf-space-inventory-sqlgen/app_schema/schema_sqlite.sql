-- SQLite Schema for Manufacturing Analytics
-- Generated from PostgreSQL schema
--
-- NOTE: The following 21 PoC tables were removed in the drop_poc_tables migration
-- (May 2026) because they were never populated with data:
--   corrective_actions, daily_deliveries, downtime_events, effectiveness_metrics,
--   equipment_metrics, equipment_reliability, failure_events, financial_impact,
--   industry_benchmarks, maintenance_targets, manufacturing_acronyms,
--   non_conformant_materials, product_defects, product_lines, production_lines,
--   production_quality, production_schedule, products, quality_costs,
--   quality_incidents, users
-- Run hf-space-inventory-sqlgen/migrations/drop_poc_tables.py to apply to
-- an existing database.

CREATE TABLE IF NOT EXISTS schema_edges (
    edge_id INTEGER NOT NULL,
    from_table TEXT,
    to_table TEXT,
    relationship_type TEXT,
    join_column TEXT,
    weight INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    join_column_description text,
    natural_language_alias TEXT,
    few_shot_example text,
    context text
);

CREATE TABLE IF NOT EXISTS schema_nodes (
    table_name TEXT NOT NULL UNIQUE,
    table_type TEXT,
    description text,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) VALUES
-- Core semantic layer tables (always present)
('EMPLOYEE',        'Table', 'Employee master records'),
('suppliers',       'Table', 'Supplier master — name, category, certification level, payment terms, lead time'),
-- ERP tables added by add_purchasing_wip_tables migration
('certification',   'Table', 'Supplier certification records (CoC, FAI, PPAP, 8130-3, Material Test Report)'),
('invoice_header',  'Table', 'AP invoice headers linked to purchase orders — three-way match and payment status'),
('labor_ticket',    'Table', 'Labor time postings against work order operations (clock-in/out, hours, cost)'),
('material_issue',  'Table', 'Raw material issues from stock to WIP work orders (quantity, unit cost, total cost)'),
('operation',       'Table', 'Work order routing steps — sequence, resource, estimated vs actual hours and costs'),
('po_line',         'Table', 'Purchase order line items (part, quantity, unit cost, line total)'),
('purchase_order',  'Table', 'Purchase order headers for material and outside-service buys'),
('receiving',       'Table', 'Goods receipts against purchase orders — quantity ordered vs received, inspection status'),
('service',         'Table', 'Outside service definitions (anodize, heat treat, NDT, plating, painting)'),
('shop_resource',   'Table', 'Shop work centers and outside-service buckets (machine, labor, service types)'),
('work_order',      'Table', 'Work order master — part, quantity, status, routing template, accumulated actual costs');

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER NOT NULL,
    supplier_name TEXT NOT NULL,
    contact_email TEXT,
    phone TEXT,
    address text,
    performance_rating REAL,
    certification_level TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ground truth query → table usage index (also created at runtime by solder_engine.py)
CREATE TABLE IF NOT EXISTS ground_truth_table_usage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_file      TEXT    NOT NULL,
    category_id     TEXT    NOT NULL,
    query_name      TEXT    NOT NULL,
    table_name      TEXT    NOT NULL,
    reference_count INTEGER NOT NULL DEFAULT 1,
    select_count    INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_gt_usage
    ON ground_truth_table_usage (category_id, query_name, table_name);

-- =============================================================================
-- SEMANTIC LAYER: Perspective & Intent Graph Constructs
-- Based on treating perspective and intent as first-class graph constructs
-- =============================================================================

-- Schema Concepts: Multiple interpretations of ambiguous fields
CREATE TABLE IF NOT EXISTS schema_concepts (
    concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_name TEXT NOT NULL UNIQUE,
    concept_type TEXT NOT NULL,  -- 'state', 'metric', 'classification', 'outcome'
    description TEXT,
    domain TEXT,  -- 'quality', 'finance', 'operations', 'compliance', 'customer'
    parent_concept_id INTEGER,  -- for REFINES relationship
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_concept_id) REFERENCES schema_concepts(concept_id)
);

-- Links fields to concepts (CAN_MEAN relationship)
CREATE TABLE IF NOT EXISTS schema_concept_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    concept_id INTEGER NOT NULL,
    is_primary_meaning INTEGER DEFAULT 0,  -- 1 = default interpretation
    context_hint TEXT,  -- when this meaning applies
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (concept_id) REFERENCES schema_concepts(concept_id),
    UNIQUE(table_name, field_name, concept_id)
);

-- Seed data: Manufacturing domain concepts
INSERT INTO schema_concepts (concept_name, concept_type, description, domain) VALUES
-- Quality domain concepts
('DefectSeverityQuality', 'classification', 'Defect severity from quality control perspective - focuses on product conformance', 'quality'),
('DefectSeverityCost', 'classification', 'Defect severity from cost impact perspective - focuses on financial exposure', 'finance'),
('DefectSeverityCustomer', 'classification', 'Defect severity from customer visibility perspective - focuses on brand risk', 'customer'),

-- Status concepts (multi-meaning)
('OrderLifecycleState', 'state', 'Order status representing lifecycle stage in fulfillment', 'operations'),
('OrderAccountingState', 'state', 'Order status from revenue recognition perspective', 'finance'),
('OrderCustomerState', 'state', 'Order status as visible to customer', 'customer'),

-- Delivery concepts
('DeliveryPerformanceOps', 'metric', 'Delivery metrics for operational planning', 'operations'),
('DeliveryPerformanceSupplier', 'metric', 'Delivery metrics for supplier scorecard', 'quality'),
('DeliveryPerformanceFinance', 'metric', 'Delivery metrics for cost/penalty calculation', 'finance'),

-- Equipment concepts
('EquipmentStateProduction', 'state', 'Equipment status for production scheduling', 'operations'),
('EquipmentStateMaintenance', 'state', 'Equipment status for maintenance planning', 'operations'),
('EquipmentStateCompliance', 'state', 'Equipment status for regulatory compliance', 'compliance'),

-- Failure concepts
('FailureSeverityProduction', 'classification', 'Failure severity based on production impact', 'operations'),
('FailureSeveritySafety', 'classification', 'Failure severity based on safety implications', 'compliance'),
('FailureSeverityCost', 'classification', 'Failure severity based on repair/replacement cost', 'finance'),

-- NCM concepts
('NCMDispositionQuality', 'outcome', 'NCM disposition from quality standpoint', 'quality'),
('NCMDispositionFinance', 'outcome', 'NCM disposition from cost recovery standpoint', 'finance'),

-- OEE concepts
('OEEOperational', 'metric', 'OEE for shift/line performance tracking', 'operations'),
('OEEStrategic', 'metric', 'OEE for capital investment decisions', 'finance');

-- Seed data: Link ambiguous fields to concepts
-- NOTE: All concept_field rows referencing empty PoC tables were removed in
-- the drop_poc_tables migration. The tables they referenced (product_defects,
-- failure_events, equipment_metrics, daily_deliveries) no longer exist.
-- Add rows here when new populated tables with ambiguous fields are onboarded.

-- Schema Perspectives: Organizational viewpoints that constrain valid meanings
CREATE TABLE IF NOT EXISTS schema_perspectives (
    perspective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    perspective_name TEXT NOT NULL UNIQUE,
    description TEXT,
    stakeholder_role TEXT,  -- typical role using this perspective
    priority_focus TEXT,    -- what this perspective prioritizes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: Which concepts each perspective uses or suppresses
CREATE TABLE IF NOT EXISTS schema_perspective_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perspective_id INTEGER NOT NULL,
    concept_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'USES_DEFINITION',  -- 'USES_DEFINITION', 'SUPPRESSES', 'EMPHASIZES'
    priority_weight INTEGER DEFAULT 1,  -- higher = more important to this perspective
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (perspective_id) REFERENCES schema_perspectives(perspective_id),
    FOREIGN KEY (concept_id) REFERENCES schema_concepts(concept_id),
    UNIQUE(perspective_id, concept_id)
);

-- Entity categories: top-level domain groupings for schema tables / graph vertices.
-- These map to the 11 ArangoDB vertex category labels and drive the pill bar in the Define Relationship UI.
CREATE TABLE IF NOT EXISTS schema_entity_categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,   -- e.g. Customer_Order, Manufacturing
    display_order INTEGER DEFAULT 99,
    description   TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_entity_categories (category_name, display_order, description) VALUES
('Customer_Order',         1,  'Customer orders, fulfilment, and delivery'),
('Demand_Forecast',        2,  'Demand planning and forecast accuracy'),
('Engineering',            3,  'Engineering change orders and BOM management'),
('General_Ledger',         4,  'GL accounts, cost centres, and financial postings'),
('Inventory_Transactions', 5,  'Stock movements, receipts, and adjustments'),
('Manufacturing',          6,  'Production orders, routing, and WIP'),
('Parts',                  7,  'Part master, revisions, and classifications'),
('Payables',               8,  'Supplier invoices and payments'),
('Receivables',            9,  'Customer invoices and collections'),
('Visual_Admin',           10, 'UI configuration and admin metadata'),
('Work_Orders',            11, 'Maintenance and shop-floor work orders');

-- Seed data: 7 Organizational Perspectives
-- IDs are explicit to prevent auto-increment from creating duplicates on re-seed.
-- Perspective taxonomy is aligned with ERP module boundaries:
--   Accounting sub-ledgers: Accounts_Payable, Accounts_Receivable, General_Ledger
--   ERP modules: Quality, Work_Orders, Manufacturing, Inventory
INSERT INTO schema_perspectives (perspective_id, perspective_name, description, stakeholder_role, priority_focus) VALUES
(1,  'Quality',               'Product conformance, defect prevention, and continuous improvement',               'Quality Engineer, QA Manager',        'Defect rates, NCM resolution, process capability'),
(2,  'Payables',             'Supplier invoices, purchase orders, vendor receipts, and payables aging.',           'AP Manager, Purchasing Manager',      'Invoice matching, payables aging, PO variance'),
(3,  'Work_Orders',          'Routing of resources in sequence on a work order (SEQUENCE_NO, RESOURCE_ID).',       'Production Planner, Shop Supervisor', 'Routing efficiency, operation sequence, outside-service cycle time'),
(4,  'General_Ledger',       'RM, WIP, FG, and COGS postings through the manufacturing cost flow.',               'Controller, Cost Accountant',         'Inventory valuation, COGS, variance analysis'),
(5,  'Receivables',          'Customer orders, sales billing, delivery commitments, and receivables exposure.',    'AR Manager, Sales Manager',           'Order fill rate, invoice aging, on-time delivery'),
(6,  'CRM',                  'Customer relationship management: contacts, accounts, opportunities, and activity.', 'Sales Rep, Account Manager',          'Pipeline, customer lifetime value, contact coverage'),
(7,  'Manufacturing',        'Production execution, schedule adherence, equipment effectiveness, and WIP.',        'Production Manager, Plant Supervisor','OEE, schedule variance, WIP turns, cycle time, downtime'),
(8,  'Inventory_Transactions','Material movements, stock receipts, material issues to WIP, and on-hand accuracy.','Materials Manager, Warehouse Supervisor','Stock accuracy, receipt qty vs ordered, material cost postings'),
(9,  'Customer_Order',       'Order fulfillment, delivery commitments, and order-lifecycle tracking.',             'Sales Manager, Customer Success',     'On-time delivery, fill rate, order-to-ship cycle time'),
(10, 'Demand_Forecast',      'Demand planning, forecast accuracy, and inventory replenishment signals.',           'Supply Chain Planner, Demand Manager','Forecast error (MAPE), bias, planning horizon coverage'),
(11, 'Engineering',          'Engineering change orders, BOM management, and part revisions.',                     'Design Engineer, Mfg Engineer',       'ECO cycle time, BOM accuracy, revision control'),
(12, 'Parts',                'Part master, revisions, classifications, and material specifications.',              'Materials Engineer, Config Manager',  'Part count, revision status, obsolescence rate'),
(13, 'Visual_Admin',         'UI configuration, admin metadata, and workspace layout settings.',                   'System Administrator',                'Config completeness, admin access, UI state');

-- Seed data: Perspective-Concept relationships (USES_DEFINITION)
-- Quality perspective uses quality-focused concepts
INSERT INTO schema_perspective_concepts (perspective_id, concept_id, relationship_type, priority_weight) VALUES
(1, 1, 'USES_DEFINITION', 3),   -- Quality uses DefectSeverityQuality (primary)
(1, 8, 'USES_DEFINITION', 2),   -- Quality uses DeliveryPerformanceSupplier
(1, 16, 'USES_DEFINITION', 3),  -- Quality uses NCMDispositionQuality

-- Accounts_Payable perspective uses cost/payables concepts
(2, 2, 'USES_DEFINITION', 3),   -- AP uses DefectSeverityCost
(2, 5, 'USES_DEFINITION', 2),   -- AP uses OrderAccountingState
(2, 9, 'USES_DEFINITION', 2),   -- AP uses DeliveryPerformanceFinance
(2, 15, 'USES_DEFINITION', 2),  -- AP uses FailureSeverityCost
(2, 17, 'USES_DEFINITION', 3),  -- AP uses NCMDispositionFinance
(2, 19, 'USES_DEFINITION', 2),  -- AP uses OEEStrategic

-- Work_Orders perspective uses routing/sequencing concepts
(3, 4, 'USES_DEFINITION', 2),   -- Work_Orders uses OrderLifecycleState
(3, 7, 'USES_DEFINITION', 3),   -- Work_Orders uses DeliveryPerformanceOps
(3, 10, 'USES_DEFINITION', 2),  -- Work_Orders uses EquipmentStateProduction
(3, 11, 'USES_DEFINITION', 2),  -- Work_Orders uses EquipmentStateMaintenance
(3, 13, 'USES_DEFINITION', 3),  -- Work_Orders uses FailureSeverityProduction
(3, 18, 'USES_DEFINITION', 3),  -- Work_Orders uses OEEOperational

-- General_Ledger perspective uses GL/cost flow concepts
(4, 12, 'USES_DEFINITION', 3),  -- GL uses EquipmentStateCompliance
(4, 14, 'USES_DEFINITION', 3),  -- GL uses FailureSeveritySafety

-- Accounts_Receivable perspective uses customer-facing concepts
(5, 3, 'USES_DEFINITION', 3),   -- AR uses DefectSeverityCustomer
(5, 6, 'USES_DEFINITION', 3),   -- AR uses OrderCustomerState
(5, 8, 'USES_DEFINITION', 2);   -- AR uses DeliveryPerformanceSupplier (for visibility)

-- Schema Intents: Analytical goals that binary-switch concept weights
-- Intent elevates one field interpretation to 1.0 while de-elevating alternatives to 0.0
CREATE TABLE IF NOT EXISTS schema_intents (
    intent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_name TEXT NOT NULL UNIQUE,
    intent_category TEXT NOT NULL,  -- maps to query categories (quality_control, supplier_performance, etc.)
    description TEXT,
    typical_question TEXT,  -- example natural language question for this intent
    primary_binding_key TEXT,  -- default binding key for SolderEngine query assembly
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: Intent-Concept weight mappings (the binary switch)
-- Weight semantics per treatise: Binary activation, NOT prioritization
--   1 = Explicitly elevated / active (use this interpretation)
--   0 = Neutral / not selected
--  -1 = Explicitly suppressed (never use this interpretation)
CREATE TABLE IF NOT EXISTS schema_intent_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL,
    concept_id INTEGER NOT NULL,
    intent_factor_weight INTEGER NOT NULL DEFAULT 0 CHECK (intent_factor_weight IN (-1, 0, 1)),
    explanation TEXT,  -- why this concept is elevated/suppressed for this intent
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES schema_intents(intent_id),
    FOREIGN KEY (concept_id) REFERENCES schema_concepts(concept_id),
    UNIQUE(intent_id, concept_id)
);

-- Link intents to ground truth SQL queries
CREATE TABLE IF NOT EXISTS schema_intent_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL,
    query_category TEXT NOT NULL,  -- maps to index.json category id
    query_file TEXT NOT NULL,      -- SQL file name
    query_index INTEGER,           -- which query in the file (0-based)
    query_name TEXT,               -- human-readable query name
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES schema_intents(intent_id)
);

-- OPERATES_WITHIN: Intent → Perspective relationship
-- Intent operates within a perspective, constraining the graph traversal path
-- Weight semantics per treatise: Binary activation, NOT prioritization
--   1 = Active path (this perspective is used)
--   0 = Neutral / not selected
--  -1 = Explicitly suppressed path
CREATE TABLE IF NOT EXISTS schema_intent_perspectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL,
    perspective_id INTEGER NOT NULL,
    intent_factor_weight INTEGER NOT NULL DEFAULT 1 CHECK (intent_factor_weight IN (-1, 0, 1)),
    explanation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES schema_intents(intent_id),
    FOREIGN KEY (perspective_id) REFERENCES schema_perspectives(perspective_id),
    UNIQUE(intent_id, perspective_id)
);

-- Seed data: Analytical Intents aligned with ground truth query categories
-- NOTE: Equipment Reliability intents (oee_operational, oee_capital_planning,
--   maintenance_scheduling) and Production Analytics intents (schedule_adherence,
--   line_efficiency, quality_cost_allocation) were removed — their query files
--   exclusively referenced empty PoC tables dropped in drop_poc_tables migration.
INSERT INTO schema_intents (intent_name, intent_category, description, typical_question) VALUES
-- Quality Control intents
('defect_cost_analysis', 'quality_control', 'Analyze defects from cost/financial impact perspective', 'What is the cost impact of defects by severity?'),
('defect_quality_trending', 'quality_control', 'Track defect rates and quality trends over time', 'What is the defect rate trend by product line?'),
('defect_customer_impact', 'quality_control', 'Assess defects from customer experience perspective', 'Which defects are most likely to reach customers?'),

-- Supplier Performance intents
('supplier_scorecard', 'supplier_performance', 'Evaluate supplier delivery and quality metrics', 'Which suppliers have the best on-time delivery?'),
('supplier_cost_penalties', 'supplier_performance', 'Analyze supplier performance for penalty/credit calculations', 'What penalties are owed for late deliveries?');

-- Seed data: Intent-Concept weight mappings (binary elevation/suppression)
-- Weight semantics: 1 = elevated, 0 = neutral, -1 = suppressed
-- For defect analysis, each intent elevates ONE severity interpretation
INSERT INTO schema_intent_concepts (intent_id, concept_id, intent_factor_weight, explanation) VALUES
-- defect_cost_analysis (intent 1) elevates DefectSeverityCost, suppresses others
(1, 1, 0, 'Quality classification not relevant for cost analysis'),
(1, 2, 1, 'ELEVATED: Cost impact interpretation for financial analysis'),
(1, 3, 0, 'Customer impact not primary for cost analysis'),

-- defect_quality_trending (intent 2) elevates DefectSeverityQuality
(2, 1, 1, 'ELEVATED: Quality classification for trending'),
(2, 2, 0, 'Cost perspective not primary for quality trending'),
(2, 3, 0, 'Customer perspective not primary for quality trending'),

-- defect_customer_impact (intent 3) elevates DefectSeverityCustomer
(3, 1, 0, 'Internal quality classification not customer-facing'),
(3, 2, 0, 'Cost impact not customer-facing'),
(3, 3, 1, 'ELEVATED: Customer experience interpretation'),

-- supplier_scorecard (intent 4) elevates DeliveryPerformanceSupplier
(4, 7, 0, 'Operational view not for supplier scoring'),
(4, 8, 1, 'ELEVATED: Supplier scorecard metrics'),
(4, 9, 0, 'Financial penalties separate from scorecard'),

-- supplier_cost_penalties (intent 5) elevates DeliveryPerformanceFinance
(5, 7, 0, 'Operational planning not for penalty calc'),
(5, 8, 0, 'Scorecard metrics not for penalty calc'),
(5, 9, 1, 'ELEVATED: Financial penalty calculations');
-- NOTE: Intents 6-11 (equipment_reliability and production_analytics categories)
-- were removed — their query files exclusively referenced empty PoC tables.

-- Seed data: Link intents to ground truth queries
INSERT INTO schema_intent_queries (intent_id, query_category, query_file, query_index, query_name) VALUES
-- Quality Control queries
(1, 'quality_control', 'quality_control.sql', 0, 'Defects by severity with cost rollup'),
(2, 'quality_control', 'quality_control.sql', 1, 'Weekly defect rate trend'),
(3, 'quality_control', 'quality_control.sql', 2, 'Customer escape risk analysis'),

-- Supplier Performance queries
(4, 'supplier_performance', 'supplier_performance.sql', 0, 'Supplier delivery scorecard'),
(5, 'supplier_performance', 'supplier_performance.sql', 1, 'Late delivery penalty calculation');
-- NOTE: Equipment Reliability and Production Analytics intent-query rows removed
-- (query files exclusively referenced empty PoC tables).

-- Seed data: OPERATES_WITHIN relationships (Intent → Perspective)
-- Maps each intent to its constraining perspective(s)
-- Weight semantics: 1 = active path, 0 = neutral, -1 = suppressed
-- Perspective IDs: 1=Quality, 2=Finance, 3=Operations, 4=Compliance, 5=Customer
INSERT INTO schema_intent_perspectives (intent_id, perspective_id, intent_factor_weight, explanation) VALUES
-- Quality Control intents
(1, 2, 1, 'defect_cost_analysis operates within Finance perspective'),
(2, 1, 1, 'defect_quality_trending operates within Quality perspective'),
(3, 5, 1, 'defect_customer_impact operates within Customer perspective'),

-- Supplier Performance intents
(4, 1, 1, 'supplier_scorecard operates within Quality perspective'),
(5, 2, 1, 'supplier_cost_penalties operates within Finance perspective');
-- NOTE: Equipment Reliability and Production Analytics intent perspectives removed
-- (intents dropped with their empty-table query files).

