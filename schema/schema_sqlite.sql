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
    status TEXT DEFAULT 'Active'::character varying,
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
    description text NOT NULL,
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
    status TEXT DEFAULT 'Open'::character varying,
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

