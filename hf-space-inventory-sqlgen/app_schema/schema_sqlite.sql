-- SQLite Schema for Manufacturing Analytics
-- Generated from PostgreSQL schema

CREATE TABLE corrective_actions (
    capa_id INTEGER NOT NULL,
    ncm_id INTEGER,
    action_description text,
    target_date DATE,
    actual_date DATE,
    effectiveness_score REAL,
    status TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_deliveries (
    delivery_id INTEGER NOT NULL,
    supplier_id INTEGER,
    delivery_date DATE NOT NULL,
    planned_quantity INTEGER,
    actual_quantity INTEGER,
    ontime_rate REAL,
    quality_score REAL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE downtime_events (
    event_id INTEGER NOT NULL,
    line_id INTEGER,
    equipment_id INTEGER,
    event_start_time DATETIME NOT NULL,
    event_end_time DATETIME,
    downtime_duration_minutes INTEGER,
    downtime_category TEXT NOT NULL,
    downtime_reason TEXT,
    impact_severity TEXT,
    production_loss_units INTEGER,
    cost_impact REAL,
    resolution_method text,
    reported_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE effectiveness_metrics (
    metric_id INTEGER NOT NULL,
    measurement_date DATE NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value REAL NOT NULL,
    target_value REAL,
    variance_percentage REAL,
    measurement_unit TEXT,
    department TEXT,
    measurement_method TEXT,
    confidence_level REAL,
    data_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment_metrics (
    equipment_id INTEGER NOT NULL,
    line_id TEXT NOT NULL,
    equipment_type TEXT,
    equipment_name TEXT,
    measurement_date DATE NOT NULL,
    availability_rate REAL,
    performance_rate REAL,
    quality_rate REAL,
    oee_score REAL,
    downtime_hours REAL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment_reliability (
    reliability_id INTEGER NOT NULL,
    equipment_id INTEGER,
    measurement_period DATE NOT NULL,
    mtbf_hours REAL,
    target_mtbf REAL,
    failure_count INTEGER,
    operating_hours REAL,
    reliability_score REAL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE failure_events (
    failure_id INTEGER NOT NULL,
    equipment_id INTEGER NOT NULL,
    failure_date DATETIME NOT NULL,
    failure_type TEXT NOT NULL,
    failure_mode TEXT,
    severity_level TEXT NOT NULL,
    downtime_hours REAL,
    repair_cost REAL,
    parts_replaced text,
    technician_assigned TEXT,
    failure_description text,
    root_cause_analysis text,
    preventive_action text,
    mtbf_impact REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE financial_impact (
    impact_id INTEGER NOT NULL,
    event_date DATE NOT NULL,
    impact_type TEXT NOT NULL,
    impact_category TEXT,
    gross_impact REAL NOT NULL,
    recovery_amount REAL DEFAULT 0,
    net_impact REAL NOT NULL,
    affected_product_lines INTEGER,
    root_cause_category TEXT,
    business_unit TEXT,
    impact_duration_days INTEGER,
    mitigation_cost REAL,
    lessons_learned text,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE industry_benchmarks (
    benchmark_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    industry_sector TEXT,
    benchmark_value REAL,
    measurement_unit TEXT,
    benchmark_class TEXT,
    last_updated DATE,
    source TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE maintenance_targets (
    target_id INTEGER NOT NULL,
    equipment_type TEXT NOT NULL,
    target_mtbf REAL,
    target_availability REAL,
    target_reliability REAL,
    maintenance_interval_hours INTEGER,
    industry_sector TEXT,
    target_class TEXT,
    last_updated DATE DEFAULT CURRENT_DATE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE manufacturing_acronyms (
    acronym_id INTEGER NOT NULL,
    acronym TEXT NOT NULL,
    definition text NOT NULL,
    table_name TEXT,
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE non_conformant_materials (
    ncm_id INTEGER NOT NULL,
    incident_date DATE NOT NULL,
    product_line TEXT,
    supplier_id INTEGER,
    material_type TEXT,
    defect_description text,
    quantity_affected INTEGER,
    severity TEXT,
    root_cause text,
    cost_impact REAL,
    status TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_defects (
    defect_id INTEGER NOT NULL,
    product_line TEXT NOT NULL,
    production_date DATE NOT NULL,
    defect_type TEXT,
    defect_count INTEGER,
    total_produced INTEGER,
    defect_rate REAL,
    severity TEXT,
    root_cause text,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_lines (
    product_line_id INTEGER NOT NULL,
    product_line_name TEXT NOT NULL,
    product_category TEXT,
    target_volume INTEGER,
    unit_price REAL,
    profit_margin REAL,
    launch_date DATE,
    lifecycle_stage TEXT,
    primary_market TEXT,
    complexity_rating TEXT,
    regulatory_requirements text,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_lines (
    line_id INTEGER NOT NULL,
    line_name TEXT NOT NULL,
    facility_location TEXT,
    line_type TEXT,
    theoretical_capacity INTEGER,
    actual_capacity INTEGER,
    efficiency_rating REAL,
    installation_date DATE,
    last_maintenance_date DATE,
    status TEXT DEFAULT 'Active',
    supervisor TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_quality (
    quality_id INTEGER NOT NULL,
    product_line TEXT NOT NULL,
    production_date DATE NOT NULL,
    defect_rate REAL,
    total_produced INTEGER,
    defect_count INTEGER,
    shift_id TEXT,
    line_supervisor TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_schedule (
    schedule_id INTEGER NOT NULL,
    line_id TEXT NOT NULL,
    product_line TEXT,
    planned_start DATETIME,
    planned_end DATETIME,
    actual_start DATETIME,
    actual_end DATETIME,
    target_quantity INTEGER,
    actual_quantity INTEGER,
    efficiency_score REAL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INTEGER NOT NULL,
    description text NOT NULL
);

CREATE TABLE quality_costs (
    cost_id INTEGER NOT NULL,
    product_line_id INTEGER,
    cost_date DATE NOT NULL,
    cost_category TEXT NOT NULL,
    cost_subcategory TEXT,
    cost_amount REAL NOT NULL,
    units_affected INTEGER,
    cost_per_unit REAL,
    cost_driver TEXT,
    prevention_opportunity text,
    department_charged TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quality_incidents (
    incident_id INTEGER NOT NULL,
    product_line TEXT NOT NULL,
    incident_date DATE NOT NULL,
    incident_type TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    affected_units INTEGER,
    cost_impact REAL,
    detection_method TEXT,
    status TEXT DEFAULT 'Open',
    assigned_to TEXT,
    resolution_date DATE,
    root_cause text,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE schema_edges (
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

CREATE TABLE schema_nodes (
    table_name TEXT NOT NULL,
    table_type TEXT,
    description text,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE suppliers (
    supplier_id INTEGER NOT NULL,
    supplier_name TEXT NOT NULL,
    contact_email TEXT,
    phone TEXT,
    address text,
    performance_rating REAL,
    certification_level TEXT,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

-- =============================================================================
-- SEMANTIC LAYER: Perspective & Intent Graph Constructs
-- Based on treating perspective and intent as first-class graph constructs
-- =============================================================================

-- Schema Concepts: Multiple interpretations of ambiguous fields
CREATE TABLE schema_concepts (
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
CREATE TABLE schema_concept_fields (
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
INSERT INTO schema_concept_fields (table_name, field_name, concept_id, is_primary_meaning, context_hint) VALUES
-- product_defects.severity mappings
('product_defects', 'severity', 1, 1, 'Default: quality control classification'),
('product_defects', 'severity', 2, 0, 'When analyzing cost impact or warranty exposure'),
('product_defects', 'severity', 3, 0, 'When assessing customer-facing risk'),

-- failure_events.severity_level mappings
('failure_events', 'severity_level', 13, 1, 'Default: production impact assessment'),
('failure_events', 'severity_level', 14, 0, 'When safety review is required'),
('failure_events', 'severity_level', 15, 0, 'When estimating repair budget'),

-- equipment_metrics.oee_score mappings
('equipment_metrics', 'oee_score', 19, 1, 'Default: daily/shift performance'),
('equipment_metrics', 'oee_score', 20, 0, 'When planning capital expenditure'),

-- daily_deliveries metrics mappings
('daily_deliveries', 'ontime_rate', 7, 1, 'Default: operational planning'),
('daily_deliveries', 'ontime_rate', 8, 0, 'When evaluating supplier performance'),
('daily_deliveries', 'ontime_rate', 9, 0, 'When calculating penalties or credits'),
('daily_deliveries', 'quality_score', 8, 1, 'Default: supplier scorecard');

-- Schema Perspectives: Organizational viewpoints that constrain valid meanings
CREATE TABLE schema_perspectives (
    perspective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    perspective_name TEXT NOT NULL UNIQUE,
    description TEXT,
    stakeholder_role TEXT,  -- typical role using this perspective
    priority_focus TEXT,    -- what this perspective prioritizes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: Which concepts each perspective uses or suppresses
CREATE TABLE schema_perspective_concepts (
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

-- Seed data: 5 Organizational Perspectives
INSERT INTO schema_perspectives (perspective_name, description, stakeholder_role, priority_focus) VALUES
('Quality', 'Product conformance, defect prevention, and continuous improvement', 'Quality Engineer, QA Manager', 'Defect rates, NCM resolution, process capability'),
('Finance', 'Cost impact, revenue recognition, and financial exposure', 'Controller, Financial Analyst', 'Cost of quality, warranty reserves, revenue timing'),
('Operations', 'Production efficiency, schedule adherence, and throughput', 'Production Manager, Plant Supervisor', 'OEE, cycle time, schedule variance'),
('Compliance', 'Regulatory requirements, safety standards, and audit readiness', 'Compliance Officer, Safety Manager', 'Regulatory adherence, safety incidents, audit findings'),
('Customer', 'Customer experience, brand perception, and delivery performance', 'Customer Success, Sales', 'On-time delivery, customer escapes, satisfaction scores');

-- Seed data: Perspective-Concept relationships (USES_DEFINITION)
-- Quality perspective uses quality-focused concepts
INSERT INTO schema_perspective_concepts (perspective_id, concept_id, relationship_type, priority_weight) VALUES
(1, 1, 'USES_DEFINITION', 3),   -- Quality uses DefectSeverityQuality (primary)
(1, 8, 'USES_DEFINITION', 2),   -- Quality uses DeliveryPerformanceSupplier
(1, 16, 'USES_DEFINITION', 3),  -- Quality uses NCMDispositionQuality

-- Finance perspective uses cost-focused concepts
(2, 2, 'USES_DEFINITION', 3),   -- Finance uses DefectSeverityCost
(2, 5, 'USES_DEFINITION', 2),   -- Finance uses OrderAccountingState
(2, 9, 'USES_DEFINITION', 2),   -- Finance uses DeliveryPerformanceFinance
(2, 15, 'USES_DEFINITION', 2),  -- Finance uses FailureSeverityCost
(2, 17, 'USES_DEFINITION', 3),  -- Finance uses NCMDispositionFinance
(2, 19, 'USES_DEFINITION', 2),  -- Finance uses OEEStrategic

-- Operations perspective uses operational concepts
(3, 4, 'USES_DEFINITION', 2),   -- Operations uses OrderLifecycleState
(3, 7, 'USES_DEFINITION', 3),   -- Operations uses DeliveryPerformanceOps
(3, 10, 'USES_DEFINITION', 2),  -- Operations uses EquipmentStateProduction
(3, 11, 'USES_DEFINITION', 2),  -- Operations uses EquipmentStateMaintenance
(3, 13, 'USES_DEFINITION', 3),  -- Operations uses FailureSeverityProduction
(3, 18, 'USES_DEFINITION', 3),  -- Operations uses OEEOperational

-- Compliance perspective uses safety/regulatory concepts
(4, 12, 'USES_DEFINITION', 3),  -- Compliance uses EquipmentStateCompliance
(4, 14, 'USES_DEFINITION', 3),  -- Compliance uses FailureSeveritySafety

-- Customer perspective uses customer-facing concepts
(5, 3, 'USES_DEFINITION', 3),   -- Customer uses DefectSeverityCustomer
(5, 6, 'USES_DEFINITION', 3),   -- Customer uses OrderCustomerState
(5, 8, 'USES_DEFINITION', 2);   -- Customer uses DeliveryPerformanceSupplier (for visibility)

-- Schema Intents: Analytical goals that binary-switch concept weights
-- Intent elevates one field interpretation to 1.0 while de-elevating alternatives to 0.0
CREATE TABLE schema_intents (
    intent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_name TEXT NOT NULL UNIQUE,
    intent_category TEXT NOT NULL,  -- maps to query categories (quality_control, supplier_performance, etc.)
    description TEXT,
    typical_question TEXT,  -- example natural language question for this intent
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: Intent-Concept weight mappings (the binary switch)
-- Weight semantics per treatise: Binary activation, NOT prioritization
--   1 = Explicitly elevated / active (use this interpretation)
--   0 = Neutral / not selected
--  -1 = Explicitly suppressed (never use this interpretation)
CREATE TABLE schema_intent_concepts (
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
CREATE TABLE schema_intent_queries (
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
CREATE TABLE schema_intent_perspectives (
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
INSERT INTO schema_intents (intent_name, intent_category, description, typical_question) VALUES
-- Quality Control intents
('defect_cost_analysis', 'quality_control', 'Analyze defects from cost/financial impact perspective', 'What is the cost impact of defects by severity?'),
('defect_quality_trending', 'quality_control', 'Track defect rates and quality trends over time', 'What is the defect rate trend by product line?'),
('defect_customer_impact', 'quality_control', 'Assess defects from customer experience perspective', 'Which defects are most likely to reach customers?'),

-- Supplier Performance intents  
('supplier_scorecard', 'supplier_performance', 'Evaluate supplier delivery and quality metrics', 'Which suppliers have the best on-time delivery?'),
('supplier_cost_penalties', 'supplier_performance', 'Analyze supplier performance for penalty/credit calculations', 'What penalties are owed for late deliveries?'),

-- Equipment Reliability intents
('oee_operational', 'equipment_reliability', 'Track OEE for shift/line performance management', 'What is the OEE trend for each production line?'),
('oee_capital_planning', 'equipment_reliability', 'Use OEE for capital investment decisions', 'Which equipment needs replacement based on OEE?'),
('maintenance_scheduling', 'equipment_reliability', 'Plan maintenance based on failure patterns', 'Which equipment is due for preventive maintenance?'),

-- Production Analytics intents
('schedule_adherence', 'production_analytics', 'Measure production schedule performance', 'How well are we meeting production schedules?'),
('line_efficiency', 'production_analytics', 'Analyze production line throughput and efficiency', 'Which lines are underperforming on throughput?'),
('quality_cost_allocation', 'production_analytics', 'Allocate quality costs to products/lines', 'What are the quality costs per product line?');

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
(5, 9, 1, 'ELEVATED: Financial penalty calculations'),

-- oee_operational (intent 6) elevates OEEOperational
(6, 18, 1, 'ELEVATED: Daily/shift OEE for operations'),
(6, 19, 0, 'Strategic OEE not for daily operations'),

-- oee_capital_planning (intent 7) elevates OEEStrategic
(7, 18, 0, 'Operational OEE not for capital planning'),
(7, 19, 1, 'ELEVATED: Strategic OEE for investment decisions'),

-- maintenance_scheduling (intent 8) elevates EquipmentStateMaintenance
(8, 10, 0, 'Production state not for maintenance scheduling'),
(8, 11, 1, 'ELEVATED: Maintenance planning state'),
(8, 12, 0, 'Compliance state not for maintenance scheduling'),

-- schedule_adherence (intent 9) elevates OrderLifecycleState
(9, 4, 1, 'ELEVATED: Order lifecycle for schedule tracking'),
(9, 5, 0, 'Accounting state not for schedule adherence'),
(9, 6, 0, 'Customer visibility not for schedule adherence'),

-- line_efficiency (intent 10) elevates OEEOperational
(10, 18, 1, 'ELEVATED: Operational OEE for line efficiency'),
(10, 19, 0, 'Strategic OEE not for line efficiency analysis'),

-- quality_cost_allocation (intent 11) elevates DefectSeverityCost
(11, 1, 0, 'Quality classification not for cost allocation'),
(11, 2, 1, 'ELEVATED: Cost impact for quality cost allocation'),
(11, 3, 0, 'Customer perspective not for cost allocation');

-- Seed data: Link intents to ground truth queries
INSERT INTO schema_intent_queries (intent_id, query_category, query_file, query_index, query_name) VALUES
-- Quality Control queries
(1, 'quality_control', 'quality_control.sql', 0, 'Defects by severity with cost rollup'),
(2, 'quality_control', 'quality_control.sql', 1, 'Weekly defect rate trend'),
(3, 'quality_control', 'quality_control.sql', 2, 'Customer escape risk analysis'),

-- Supplier Performance queries
(4, 'supplier_performance', 'supplier_performance.sql', 0, 'Supplier delivery scorecard'),
(5, 'supplier_performance', 'supplier_performance.sql', 1, 'Late delivery penalty calculation'),

-- Equipment Reliability queries
(6, 'equipment_reliability', 'equipment_reliability.sql', 0, 'Daily OEE by line'),
(7, 'equipment_reliability', 'equipment_reliability.sql', 1, 'Equipment replacement candidates'),
(8, 'equipment_reliability', 'equipment_reliability.sql', 2, 'Maintenance schedule gaps'),

-- Production Analytics queries
(9, 'production_analytics', 'production_analytics.sql', 0, 'Schedule adherence report'),
(10, 'production_analytics', 'production_analytics.sql', 1, 'Line efficiency comparison'),
(11, 'production_analytics', 'production_analytics.sql', 2, 'Quality cost by product');

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
(5, 2, 1, 'supplier_cost_penalties operates within Finance perspective'),

-- Equipment Reliability intents
(6, 3, 1, 'oee_operational operates within Operations perspective'),
(7, 2, 1, 'oee_capital_planning operates within Finance perspective'),
(8, 3, 1, 'maintenance_scheduling operates within Operations perspective'),

-- Production Analytics intents
(9, 3, 1, 'schedule_adherence operates within Operations perspective'),
(10, 3, 1, 'line_efficiency operates within Operations perspective'),
(11, 2, 1, 'quality_cost_allocation operates within Finance perspective');

