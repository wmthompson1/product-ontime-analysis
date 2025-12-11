












CREATE TABLE IF NOT EXISTS corrective_actions (
    capa_id integer NOT NULL,
    ncm_id integer,
    action_description TEXT,
    target_date TEXT,
    actual_date TEXT,
    effectiveness_score NUMERIC,
    status TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS daily_deliveries (
    delivery_id integer NOT NULL,
    supplier_id integer,
    delivery_date TEXT NOT NULL,
    planned_quantity integer,
    actual_quantity integer,
    ontime_rate NUMERIC,
    quality_score NUMERIC,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS downtime_events (
    event_id integer NOT NULL,
    line_id integer,
    equipment_id integer,
    event_start_time DATETIME NOT NULL,
    event_end_time DATETIME,
    downtime_duration_minutes integer,
    downtime_category TEXT NOT NULL,
    downtime_reason TEXT,
    impact_severity TEXT,
    production_loss_units integer,
    cost_impact NUMERIC,
    resolution_method TEXT,
    reported_by TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS effectiveness_metrics (
    metric_id integer NOT NULL,
    measurement_date TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    target_value NUMERIC,
    variance_percentage NUMERIC,
    measurement_unit TEXT,
    department TEXT,
    measurement_method TEXT,
    confidence_level NUMERIC,
    data_source TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS equipment_metrics (
    equipment_id integer NOT NULL,
    line_id TEXT NOT NULL,
    equipment_type TEXT,
    equipment_name TEXT,
    measurement_date TEXT NOT NULL,
    availability_rate NUMERIC,
    performance_rate NUMERIC,
    quality_rate NUMERIC,
    oee_score NUMERIC,
    downtime_hours NUMERIC,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS equipment_reliability (
    reliability_id integer NOT NULL,
    equipment_id integer,
    measurement_period TEXT NOT NULL,
    mtbf_hours NUMERIC,
    target_mtbf NUMERIC,
    failure_count integer,
    operating_hours NUMERIC,
    reliability_score NUMERIC,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS failure_events (
    failure_id integer NOT NULL,
    equipment_id integer NOT NULL,
    failure_date DATETIME NOT NULL,
    failure_type TEXT NOT NULL,
    failure_mode TEXT,
    severity_level TEXT NOT NULL,
    downtime_hours NUMERIC,
    repair_cost NUMERIC,
    parts_replaced TEXT,
    technician_assigned TEXT,
    failure_description TEXT,
    root_cause_analysis TEXT,
    preventive_action TEXT,
    mtbf_impact NUMERIC,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS financial_impact (
    impact_id integer NOT NULL,
    event_date TEXT NOT NULL,
    impact_type TEXT NOT NULL,
    impact_category TEXT,
    gross_impact NUMERIC NOT NULL,
    recovery_amount NUMERIC DEFAULT 0,
    net_impact NUMERIC NOT NULL,
    affected_product_lines integer,
    root_cause_category TEXT,
    business_unit TEXT,
    impact_duration_days integer,
    mitigation_cost NUMERIC,
    lessons_learned TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS industry_benchmarks (
    benchmark_id integer NOT NULL,
    metric_name TEXT NOT NULL,
    industry_sector TEXT,
    benchmark_value NUMERIC,
    measurement_unit TEXT,
    benchmark_class TEXT,
    last_updated TEXT,
    source TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS maintenance_targets (
    target_id integer NOT NULL,
    equipment_type TEXT NOT NULL,
    target_mtbf NUMERIC,
    target_availability NUMERIC,
    target_reliability NUMERIC,
    maintenance_interval_hours integer,
    industry_sector TEXT,
    target_class TEXT,
    last_updated TEXT DEFAULT CURRENT_DATE,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS manufacturing_acronyms (
    acronym_id integer NOT NULL,
    acronym TEXT NOT NULL,
    definition TEXT NOT NULL,
    table_name TEXT,
    category TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS non_conformant_materials (
    ncm_id integer NOT NULL,
    incident_date TEXT NOT NULL,
    product_line TEXT,
    supplier_id integer,
    material_type TEXT,
    defect_description TEXT,
    quantity_affected integer,
    severity TEXT,
    root_cause TEXT,
    cost_impact NUMERIC,
    status TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS product_defects (
    defect_id integer NOT NULL,
    product_line TEXT NOT NULL,
    production_date TEXT NOT NULL,
    defect_type TEXT,
    defect_count integer,
    total_produced integer,
    defect_rate NUMERIC,
    severity TEXT,
    root_cause TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS product_lines (
    product_line_id integer NOT NULL,
    product_line_name TEXT NOT NULL,
    product_category TEXT,
    target_volume integer,
    unit_price NUMERIC,
    profit_margin NUMERIC,
    launch_date TEXT,
    lifecycle_stage TEXT,
    primary_market TEXT,
    complexity_rating TEXT,
    regulatory_requirements TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS production_lines (
    line_id integer NOT NULL,
    line_name TEXT NOT NULL,
    facility_location TEXT,
    line_type TEXT,
    theoretical_capacity integer,
    actual_capacity integer,
    efficiency_rating NUMERIC,
    installation_date TEXT,
    last_maintenance_date TEXT,
    status TEXT DEFAULT 'Active', 
    supervisor TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS production_quality (
    quality_id integer NOT NULL,
    product_line TEXT NOT NULL,
    production_date TEXT NOT NULL,
    defect_rate NUMERIC,
    total_produced integer,
    defect_count integer,
    shift_id TEXT,
    line_supervisor TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS production_schedule (
    schedule_id integer NOT NULL,
    line_id TEXT NOT NULL,
    product_line TEXT,
    planned_start DATETIME,
    planned_end DATETIME,
    actual_start DATETIME,
    actual_end DATETIME,
    target_quantity integer,
    actual_quantity integer,
    efficiency_score NUMERIC,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS products (
    id integer NOT NULL,
    description TEXT NOT NULL
);







CREATE TABLE IF NOT EXISTS quality_costs (
    cost_id integer NOT NULL,
    product_line_id integer,
    cost_date TEXT NOT NULL,
    cost_category TEXT NOT NULL,
    cost_subcategory TEXT,
    cost_amount NUMERIC NOT NULL,
    units_affected integer,
    cost_per_unit NUMERIC,
    cost_driver TEXT,
    prevention_opportunity TEXT,
    department_charged TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS quality_incidents (
    incident_id integer NOT NULL,
    product_line TEXT NOT NULL,
    incident_date TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    affected_units integer,
    cost_impact NUMERIC,
    detection_method TEXT,
    status TEXT DEFAULT 'Open', 
    assigned_to TEXT,
    resolution_date TEXT,
    root_cause TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS schema_edges (
    edge_id integer NOT NULL,
    from_table TEXT,
    to_table TEXT,
    relationship_type TEXT,
    join_column TEXT,
    weight integer DEFAULT 1,
    created_at DATETIME DEFAULT (datetime('now')),
    join_column_description TEXT,
    natural_language_alias TEXT,
    few_shot_example TEXT,
    context TEXT
);







CREATE TABLE IF NOT EXISTS schema_nodes (
    table_name TEXT NOT NULL,
    table_type TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);




CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id integer NOT NULL,
    supplier_name TEXT NOT NULL,
    contact_email TEXT,
    phone TEXT,
    address TEXT,
    performance_rating NUMERIC,
    certification_level TEXT,
    created_date DATETIME DEFAULT (datetime('now'))
);







CREATE TABLE IF NOT EXISTS users (
    id integer NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);


























































































































































CREATE INDEX IF NOT EXISTS idx_acronym ON manufacturing_acronyms (acronym);



CREATE INDEX IF NOT EXISTS idx_table_name ON manufacturing_acronyms (table_name);

































ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;



\unrestrict uzPEdw0gykufkLv7yMcJF3t2kTKlaIvTv8iXUwtHIPAVGbI6sDWDGRaOobUg7i7