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
    edge_id                INTEGER PRIMARY KEY,   -- unique FK edge id; INSERT OR IGNORE is idempotent
    from_table             TEXT,
    to_table               TEXT,
    relationship_type      TEXT,
    join_column            TEXT,
    weight                 INTEGER DEFAULT 1,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    join_column_description TEXT,
    natural_language_alias TEXT,
    few_shot_example       TEXT,
    context                TEXT
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
-- Purchasing / WIP digital twin — master data
('part',            'Table', 'Part / item master — description, class, UOM, cost, revision, material spec, CAGE code'),
('suppliers',       'Table', 'Supplier master — name, category, certification level, payment terms, lead time'),
('shop_resource',   'Table', 'Shop work centers and outside-service buckets (machine, labor, service types)'),
('service',         'Table', 'Outside service definitions (anodize, heat treat, NDT, plating, painting)'),
-- Purchasing / WIP digital twin — transactional
('purchase_order',  'Table', 'Purchase order headers for material and outside-service buys'),
('po_line',         'Table', 'Purchase order line items (part, quantity, unit cost, line total)'),
('receiving',       'Table', 'Goods receipts against purchase orders — quantity ordered vs received, inspection status'),
('invoice_header',  'Table', 'AP invoice headers linked to purchase orders — three-way match and payment status'),
('certification',   'Table', 'Supplier certification records (CoC, FAI, PPAP, 8130-3, Material Test Report)'),
('work_order',      'Table', 'Work order master — part, quantity, status, routing template, accumulated actual costs'),
('operation',       'Table', 'Work order routing steps — sequence, resource, estimated vs actual hours and costs'),
('material_issue',  'Table', 'Raw material issues from stock to WIP work orders (quantity, unit cost, total cost)'),
('labor_ticket',    'Table', 'Labor time postings against work order operations (clock-in/out, hours, cost)'),
('requirement',     'Table', 'Resource requirements (labor / material / burden) per routing operation; component_type PART = as-designed routing standard (engineering, per-unit) vs WORK_ORDER = as-built actuals (manufacturing, batch)');

-- ─────────────────────────────────────────────────────────────────────────────
-- FK EDGE REGISTRY  (used by graph_sync to build containment / join graph)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_edges
    (edge_id, from_table, to_table, relationship_type, join_column, weight, natural_language_alias) VALUES
-- Purchasing chain
(1,  'po_line',       'purchase_order', 'FOREIGN_KEY', 'po_id',        1, 'PO lines belong to a purchase order'),
(2,  'po_line',       'part',           'FOREIGN_KEY', 'part_id',       1, 'PO line references a part'),
(3,  'receiving',     'purchase_order', 'FOREIGN_KEY', 'po_id',         1, 'Receipt closes against a purchase order'),
(4,  'receiving',     'suppliers',      'FOREIGN_KEY', 'supplier_id',   1, 'Receipt records the delivering supplier'),
(5,  'receiving',     'part',           'FOREIGN_KEY', 'part_id',       1, 'Receipt records the received part'),
(6,  'invoice_header','purchase_order', 'FOREIGN_KEY', 'po_id',         1, 'Invoice matches to a purchase order'),
(7,  'invoice_header','suppliers',      'FOREIGN_KEY', 'supplier_id',   1, 'Invoice issued by a supplier'),
(8,  'purchase_order','suppliers',      'FOREIGN_KEY', 'supplier_id',   1, 'Purchase order placed with a supplier'),
(9,  'certification', 'receiving',      'FOREIGN_KEY', 'receipt_id',    1, 'Cert attached to a receiving line'),
(10, 'certification', 'part',           'FOREIGN_KEY', 'part_id',       1, 'Cert covers a specific part'),
-- WIP chain
(11, 'work_order',    'part',           'FOREIGN_KEY', 'part_id',       1, 'Work order manufactures a part'),
(12, 'operation',     'work_order',     'FOREIGN_KEY', 'wo_id',         1, 'Routing step belongs to a work order'),
(13, 'operation',     'shop_resource',  'FOREIGN_KEY', 'resource_id',   1, 'Routing step runs on a shop resource'),
(14, 'material_issue','work_order',     'FOREIGN_KEY', 'wo_id',         1, 'Material issued to a work order'),
(15, 'material_issue','part',           'FOREIGN_KEY', 'part_id',       1, 'Material issue consumes a part'),
(16, 'labor_ticket',  'work_order',     'FOREIGN_KEY', 'wo_id',         1, 'Labor ticket posted against a work order'),
-- Outside service cross-link
(17, 'purchase_order','work_order',     'FOREIGN_KEY', 'wo_id',         1, 'Outside-service PO tied to a work order'),
(18, 'operation',     'service',        'FOREIGN_KEY', 'service_id',    1, 'Outside-service op uses a service definition'),
(19, 'operation',     'suppliers',      'FOREIGN_KEY', 'vendor_id',     1, 'Outside-service op dispatched to a supplier'),
-- Requirement chain (engineering vs manufacturing differentiator on component_type)
(20, 'requirement',   'operation',      'FOREIGN_KEY', 'operation_rowid', 1, 'Requirement consumed at a routing operation (work-order level)'),
(21, 'requirement',   'part',           'FOREIGN_KEY', 'material_part_id', 1, 'Material requirement consumes a part'),
(22, 'requirement',   'part',           'FOREIGN_KEY', 'component_id',   1, 'Design-level requirement belongs to a part component (engineering)'),
(23, 'requirement',   'work_order',     'FOREIGN_KEY', 'component_id',   1, 'Work-order-level requirement belongs to a work order component (manufacturing)');

-- ─────────────────────────────────────────────────────────────────────────────
-- ERP TABLE DDL  (aerospace manufacturing — Purchasing / WIP digital twin)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS part (
    part_id          TEXT PRIMARY KEY,          -- e.g. P-12345
    part_description TEXT NOT NULL,
    part_class       TEXT NOT NULL CHECK(part_class IN ('RAW','HARDWARE','MAKE','BUY','OUTSIDE_SERVICE')),
    unit_of_measure  TEXT NOT NULL DEFAULT 'EA',  -- EA / LB / FT / IN
    unit_cost        REAL DEFAULT 0.0,
    lead_time_days   INTEGER DEFAULT 0,
    reorder_point    REAL DEFAULT 0.0,
    on_hand_qty      REAL DEFAULT 0.0,
    revision         TEXT DEFAULT 'A',           -- drawing revision level
    cage_code        TEXT,                        -- 5-char CAGE code (aerospace supplier ID)
    drawing_number   TEXT,
    material_spec    TEXT,                        -- e.g. AMS 4928 / 6061-T6 / 304 SS
    active           INTEGER DEFAULT 1,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name      TEXT NOT NULL,
    contact_email      TEXT,
    phone              TEXT,
    address            TEXT,
    performance_rating REAL DEFAULT 0.0,
    certification_level TEXT,                    -- AS9100D / ISO9001 / NADCAP / etc.
    category           TEXT,                     -- material / outside_service / hardware
    payment_terms      TEXT DEFAULT 'Net30',
    lead_time_days     INTEGER DEFAULT 14,
    outside_service    INTEGER DEFAULT 0,        -- 1 = primarily an outside-service vendor
    active             INTEGER DEFAULT 1,
    created_date       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_order (
    po_id         TEXT PRIMARY KEY,              -- e.g. PO-240001
    supplier_id   TEXT NOT NULL,                 -- FK → suppliers
    po_type       TEXT NOT NULL CHECK(po_type IN ('material','outside_service')),
    po_date       DATE NOT NULL,
    required_date DATE,
    status        TEXT NOT NULL,                 -- Open / Partial / Closed / Cancelled
    total_cost    REAL DEFAULT 0.0,
    wo_id         TEXT,                          -- FK → work_order (outside_service POs)
    service_id    TEXT,                          -- FK → service (outside_service POs)
    buyer_id      TEXT DEFAULT 'BUYER-1',
    site_id       TEXT DEFAULT 'SITE-1',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS po_line (
    line_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id            TEXT NOT NULL,              -- FK → purchase_order
    part_id          TEXT NOT NULL,              -- FK → part
    part_description TEXT NOT NULL,
    quantity         REAL NOT NULL,
    unit_cost        REAL NOT NULL,
    line_total       REAL NOT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receiving (
    receipt_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id             TEXT NOT NULL,             -- FK → purchase_order
    supplier_id       TEXT NOT NULL,             -- FK → suppliers
    part_id           TEXT NOT NULL,             -- FK → part
    quantity_ordered  REAL NOT NULL,
    quantity_received REAL NOT NULL,
    receipt_date      DATE NOT NULL,
    inspection_status TEXT NOT NULL DEFAULT 'Pending',  -- Pending / Passed / Failed / Waived
    cert_required     INTEGER DEFAULT 0,         -- 1 = CoC / FAI / 8130-3 required
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_header (
    invoice_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id                  TEXT NOT NULL,        -- FK → purchase_order
    supplier_id            TEXT NOT NULL,        -- FK → suppliers
    invoice_number         TEXT NOT NULL UNIQUE,
    invoice_date           DATE NOT NULL,
    due_date               DATE NOT NULL,
    amount_dollars         REAL NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'Open',  -- Open / Paid / Disputed / Void
    payment_date           DATE,
    three_way_match_status TEXT DEFAULT 'Pending',        -- Pending / Matched / Exception
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS certification (
    cert_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id  INTEGER,                         -- FK → receiving (NULL = stand-alone cert)
    part_id     TEXT NOT NULL,                   -- FK → part
    supplier_id TEXT NOT NULL,                   -- FK → suppliers
    cert_type   TEXT NOT NULL,                   -- CoC / FAI / PPAP / 8130-3 / Material_Test_Report
    issued_date DATE NOT NULL,
    expiry_date DATE,
    status      TEXT DEFAULT 'Active' CHECK(status IN ('Active','Expired','Revoked')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_resource (
    resource_id     TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    resource_type   TEXT NOT NULL CHECK(resource_type IN ('M','L','S')),
    -- M=Machine  L=Labor  S=Outside Service bucket
    run_cost_per_hr REAL DEFAULT 0.0,
    bur_per_hr_run  REAL DEFAULT 0.0,
    active          INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service (
    service_id     TEXT PRIMARY KEY,
    description    TEXT NOT NULL,
    default_vendor TEXT,                         -- FK → suppliers
    base_charge    REAL DEFAULT 0.0,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_order (
    wo_id            TEXT PRIMARY KEY,           -- e.g. WO-240001
    workorder_type   TEXT NOT NULL CHECK(workorder_type IN ('M','W')),
    -- M=Manufacturing  W=Rework
    part_id          TEXT NOT NULL,              -- FK → part
    part_description TEXT NOT NULL,
    quantity         REAL NOT NULL,
    status           TEXT NOT NULL,              -- Open / Released / Closed / Cancelled
    open_date        DATE,
    close_date       DATE,
    required_date    DATE,
    routing_template TEXT,                       -- AIRFRAME / FASTENER / MACHINED / WELDMENT
    act_lab_cost     REAL DEFAULT 0.0,
    act_bur_cost     REAL DEFAULT 0.0,
    act_ser_cost     REAL DEFAULT 0.0,
    act_mat_cost     REAL DEFAULT 0.0,
    outside_service  INTEGER DEFAULT 0,          -- 1 if any op routes outside
    site_id          TEXT DEFAULT 'SITE-1',
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operation (
    rowid_pk           INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_id              TEXT NOT NULL,            -- FK → work_order
    workorder_type     TEXT NOT NULL,
    sequence_no        INTEGER NOT NULL,         -- multiples of 10
    resource_id        TEXT NOT NULL,            -- FK → shop_resource
    service_id         TEXT,                     -- FK → service (outside ops only)
    vendor_id          TEXT,                     -- FK → suppliers (outside ops only)
    run_type           TEXT DEFAULT 'HR',        -- HR=per hour  PC=per piece
    setup_hrs          REAL DEFAULT 0.0,
    run_hrs            REAL DEFAULT 0.0,
    act_setup_hrs      REAL DEFAULT 0.0,
    act_run_hrs        REAL DEFAULT 0.0,
    est_atl_lab_cost   REAL DEFAULT 0.0,
    est_atl_bur_cost   REAL DEFAULT 0.0,
    est_atl_ser_cost   REAL DEFAULT 0.0,
    act_atl_lab_cost   REAL DEFAULT 0.0,
    act_atl_bur_cost   REAL DEFAULT 0.0,
    act_atl_ser_cost   REAL DEFAULT 0.0,
    status             TEXT DEFAULT 'Q',         -- Q=Queued  S=Started  C=Complete
    sched_start_date   DATETIME,
    sched_finish_date  DATETIME,
    service_begin_date DATETIME,
    close_date         DATETIME,
    last_disp_date     DATETIME,                 -- last outside-service dispatch date
    last_recv_date     DATETIME,                 -- last outside-service receipt date
    UNIQUE(wo_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS material_issue (
    issue_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_id            TEXT NOT NULL,              -- FK → work_order
    part_id          TEXT NOT NULL,              -- FK → part
    part_description TEXT NOT NULL,
    quantity         REAL NOT NULL,
    unit_cost        REAL NOT NULL,
    total_cost       REAL NOT NULL,
    issue_date       DATE NOT NULL,
    issued_by        TEXT NOT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS labor_ticket (
    ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_id       TEXT NOT NULL,                   -- FK → work_order
    sequence_no INTEGER NOT NULL,                -- matches operation.sequence_no
    employee_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,                   -- FK → shop_resource
    clock_in    DATETIME NOT NULL,
    clock_out   DATETIME NOT NULL,
    total_hours REAL NOT NULL,
    labor_cost  REAL NOT NULL,                   -- total_hours × run_cost_per_hr
    burden_cost REAL NOT NULL,                   -- total_hours × bur_per_hr_run
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Requirement: resource demand (labor / material / burden) per routing operation.
-- component_type is the ENGINEERING vs MANUFACTURING differentiator:
--   PART       -> design level (as-designed routing standard; engineering, per-unit basis)
--   WORK_ORDER -> work-order level (as-built actuals; manufacturing, batch basis)
CREATE TABLE IF NOT EXISTS requirement (
    requirement_id    TEXT PRIMARY KEY,                  -- e.g. REQ-000001
    component_type    TEXT NOT NULL CHECK(component_type IN ('PART','WORK_ORDER')),
    component_id      TEXT NOT NULL,                     -- part_id (design) or wo_id (work order)
    requirement_level TEXT NOT NULL CHECK(requirement_level IN ('DESIGN','WORK_ORDER')),
    requirement_type  TEXT NOT NULL CHECK(requirement_type IN ('LABOR','MATERIAL','BURDEN')),
    operation_seq     INTEGER NOT NULL,                  -- routing sequence step (multiples of 10); design-level operation handle
    operation_rowid   INTEGER,                           -- FK -> operation (work-order-level concrete op; NULL at design level)
    material_part_id  TEXT,                              -- FK -> part when requirement_type='MATERIAL'
    std_qty           REAL DEFAULT 0.0,                  -- per-unit standard quantity / hours (as-designed)
    actual_qty        REAL DEFAULT 0.0,                  -- actual consumed (as-built, work-order)
    unit_cost         REAL DEFAULT 0.0,
    extended_cost     REAL DEFAULT 0.0,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("operation_rowid") REFERENCES "operation" ("rowid_pk"),
    FOREIGN KEY ("material_part_id") REFERENCES "part" ("part_id")
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
-- NOTE: Only perspective-concept pairs whose concept_id exists in the curated
-- schema_concepts set are seeded. Earlier seed rows referencing concept_ids
-- 4,5,6,10-19 pointed to concepts that were later removed/re-keyed during
-- curation, leaving orphaned (dead-FK) bridge rows that could never become
-- graph edges. Those 13 obsolete pairs were dropped so the SQLite source
-- matches the active concept definitions (and the ArangoDB projection).
INSERT INTO schema_perspective_concepts (perspective_id, concept_id, relationship_type, priority_weight) VALUES
(1, 1, 'USES_DEFINITION', 3),   -- Quality uses DefectSeverityQuality (primary)
(1, 8, 'USES_DEFINITION', 2),   -- Quality uses DeliveryPerformanceSupplier

-- Accounts_Payable perspective uses cost/payables concepts
(2, 2, 'USES_DEFINITION', 3),   -- AP uses DefectSeverityCost
(2, 9, 'USES_DEFINITION', 2),   -- AP uses DeliveryPerformanceFinance

-- Work_Orders perspective uses routing/sequencing concepts
(3, 7, 'USES_DEFINITION', 3),   -- Work_Orders uses DeliveryPerformanceOps

-- Accounts_Receivable perspective uses customer-facing concepts
(5, 3, 'USES_DEFINITION', 3),   -- AR uses DefectSeverityCustomer
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

-- =============================================================================
-- APP METADATA TABLES (Plan-009)
-- These three tables are the SQLite source of truth for DAB field definitions
-- and graph topology annotations.  dab_config.json is a synced artifact, not
-- a source of truth.  Excluded from get_all_tables() via APP_METADATA_TABLES.
-- =============================================================================

-- API / DAB field descriptions: display name, description, and example value
-- keyed on the four-part column identity.
CREATE TABLE IF NOT EXISTS api_field_descriptions (
    source_database TEXT    NOT NULL,
    schema_name     TEXT    NOT NULL,
    table_name      TEXT    NOT NULL,
    column_name     TEXT    NOT NULL,
    display_name    TEXT,
    description     TEXT,
    example_value   TEXT,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_database, schema_name, table_name, column_name)
);

-- Structural containment topology annotations: records the intended edge type
-- between node pairs in the containment graph (database → schema → table → column).
CREATE TABLE IF NOT EXISTS schema_topology_metadata (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_node_type TEXT    NOT NULL CHECK(source_node_type IN ('database', 'schema', 'table', 'column')),
    target_node_type TEXT    NOT NULL CHECK(target_node_type IN ('database', 'schema', 'table', 'column')),
    source_key       TEXT    NOT NULL,
    target_key       TEXT    NOT NULL,
    edge_predicate   TEXT    NOT NULL DEFAULT 'CONTAINS',
    weight           INTEGER NOT NULL DEFAULT 1,
    notes            TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_node_type, target_node_type, source_key, target_key, edge_predicate)
);

-- DAB field definitions: certified, SME-approved field definition text keyed
-- on the same four-part column identity as api_field_descriptions.
CREATE TABLE IF NOT EXISTS dab_field_definitions (
    source_database  TEXT    NOT NULL,
    schema_name      TEXT    NOT NULL,
    table_name       TEXT    NOT NULL,
    column_name      TEXT    NOT NULL,
    field_definition TEXT,
    certified        INTEGER NOT NULL DEFAULT 0 CHECK(certified IN (0, 1)),
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_database, schema_name, table_name, column_name)
);

-- SQL graph source tables: hold the full canonical graph (nodes + edges in the
-- fixed 6-slot composite-key form) that replit_integrations/export_graph_metadata.py
-- materializes and then serializes graph_metadata.json FROM. SQLite is the source
-- of truth; the JSON is provably a dump of these rows. One column per JSON field;
-- columns that apply to only one node/edge kind are NULL for the others. The
-- ordinal column preserves the exact JSON emission order on read-back.
CREATE TABLE IF NOT EXISTS sql_graph_nodes (
    ordinal       INTEGER NOT NULL,
    _key          TEXT    NOT NULL PRIMARY KEY,
    _id           TEXT    NOT NULL,
    node_type     TEXT    NOT NULL CHECK(node_type IN ('table', 'column')),
    node_family   TEXT    NOT NULL,
    perspective   TEXT    NOT NULL,
    table_name    TEXT    NOT NULL,
    column_name   TEXT,
    column_slot   TEXT,
    predicate     TEXT    NOT NULL,
    unique_id     TEXT    NOT NULL,
    description   TEXT,
    column_type   TEXT,
    "notnull"     INTEGER,
    default_value TEXT,
    primary_key   INTEGER,
    foreign_key   INTEGER
);

CREATE TABLE IF NOT EXISTS sql_graph_edges (
    ordinal           INTEGER NOT NULL,
    _key              TEXT    NOT NULL PRIMARY KEY,
    _id               TEXT    NOT NULL,
    _from             TEXT    NOT NULL,
    _to               TEXT    NOT NULL,
    edge_family       TEXT    NOT NULL,
    edge_type         TEXT    NOT NULL CHECK(edge_type IN ('has_column', 'references', 'elevates')),
    perspective       TEXT    NOT NULL,
    unique_id         TEXT    NOT NULL,
    references_table  TEXT,
    references_column TEXT,
    weight            INTEGER,
    concept           TEXT
);

-- SME-authored canonical edges (Define Relationship UI source of truth).
-- Durable input table: the exporter MERGES these into the materialized
-- sql_graph_edges every run, so authored relationships survive a re-export
-- (sql_graph_edges itself is delete+reinsert each export). Absent columns are
-- stored as '' (not NULL) so the UNIQUE constraint dedupes correctly.
CREATE TABLE IF NOT EXISTS sql_graph_authored_edges (
    authored_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_type     TEXT    NOT NULL CHECK(edge_type IN ('has_column', 'references', 'elevates')),
    from_table    TEXT    NOT NULL,
    from_column   TEXT    NOT NULL DEFAULT '',
    to_table      TEXT    NOT NULL,
    to_column     TEXT    NOT NULL DEFAULT '',
    perspective   TEXT    NOT NULL DEFAULT 'system',
    weight        INTEGER,
    concept       TEXT,
    created_by    TEXT    NOT NULL DEFAULT 'define_relationship_ui',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(edge_type, from_table, from_column, to_table, to_column, perspective)
);

-- Column bindings: maps semantic intent slots to physical columns.
-- Created here as an additive guard; populated by the solder engine.
CREATE TABLE IF NOT EXISTS column_bindings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_name     TEXT    NOT NULL,
    slot_name       TEXT    NOT NULL,
    table_name      TEXT    NOT NULL,
    column_name     TEXT    NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(intent_name, slot_name)
);
