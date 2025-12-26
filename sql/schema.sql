-- Product On-Time Analysis Database Schema
-- This schema supports tracking of suppliers, parts, assemblies, products, and delivery performance

-- Suppliers table
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(200) NOT NULL,
    supplier_code VARCHAR(50) UNIQUE NOT NULL,
    country VARCHAR(100),
    contact_email VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parts table
CREATE TABLE IF NOT EXISTS parts (
    part_id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    part_name VARCHAR(200) NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(supplier_id),
    unit_cost NUMERIC(10, 2),
    lead_time_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    product_family VARCHAR(100),
    target_cycle_time_hours INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assemblies table (bill of materials)
CREATE TABLE IF NOT EXISTS assemblies (
    assembly_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(product_id),
    part_id INTEGER REFERENCES parts(part_id),
    quantity_required INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, part_id)
);

-- Deliveries table
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id SERIAL PRIMARY KEY,
    part_id INTEGER REFERENCES parts(part_id),
    delivery_date DATE NOT NULL,
    quantity_received INTEGER NOT NULL,
    quantity_expected INTEGER NOT NULL,
    days_late INTEGER DEFAULT 0,
    is_on_time BOOLEAN GENERATED ALWAYS AS (days_late <= 0) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Production runs table
CREATE TABLE IF NOT EXISTS production_runs (
    run_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(product_id),
    run_date DATE NOT NULL,
    quantity_produced INTEGER NOT NULL,
    quantity_defective INTEGER DEFAULT 0,
    defect_rate NUMERIC(5, 4) GENERATED ALWAYS AS (
        CASE 
            WHEN quantity_produced > 0 THEN quantity_defective::NUMERIC / quantity_produced
            ELSE 0
        END
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality metrics table
CREATE TABLE IF NOT EXISTS quality_metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES production_runs(run_id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(10, 4),
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_parts_supplier ON parts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_assemblies_product ON assemblies(product_id);
CREATE INDEX IF NOT EXISTS idx_assemblies_part ON assemblies(part_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_part ON deliveries(part_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_date ON deliveries(delivery_date);
CREATE INDEX IF NOT EXISTS idx_production_runs_product ON production_runs(product_id);
CREATE INDEX IF NOT EXISTS idx_production_runs_date ON production_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_quality_metrics_run ON quality_metrics(run_id);

-- Create views for common analytics queries

-- Supplier performance view
CREATE OR REPLACE VIEW supplier_performance AS
SELECT 
    s.supplier_id,
    s.supplier_name,
    s.supplier_code,
    COUNT(DISTINCT d.delivery_id) as total_deliveries,
    SUM(CASE WHEN d.is_on_time THEN 1 ELSE 0 END) as on_time_deliveries,
    ROUND(
        100.0 * SUM(CASE WHEN d.is_on_time THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(d.delivery_id), 0), 
        2
    ) as on_time_percentage,
    AVG(d.days_late) as avg_days_late
FROM suppliers s
LEFT JOIN parts p ON s.supplier_id = p.supplier_id
LEFT JOIN deliveries d ON p.part_id = d.part_id
GROUP BY s.supplier_id, s.supplier_name, s.supplier_code;

-- Product quality view
CREATE OR REPLACE VIEW product_quality AS
SELECT 
    p.product_id,
    p.product_code,
    p.product_name,
    COUNT(pr.run_id) as total_runs,
    SUM(pr.quantity_produced) as total_produced,
    SUM(pr.quantity_defective) as total_defective,
    ROUND(
        100.0 * SUM(pr.quantity_defective) / 
        NULLIF(SUM(pr.quantity_produced), 0),
        4
    ) as overall_defect_rate
FROM products p
LEFT JOIN production_runs pr ON p.product_id = pr.product_id
GROUP BY p.product_id, p.product_code, p.product_name;

-- Daily delivery summary view
CREATE OR REPLACE VIEW daily_delivery_summary AS
SELECT 
    delivery_date,
    COUNT(*) as total_deliveries,
    SUM(quantity_received) as total_received,
    SUM(CASE WHEN is_on_time THEN quantity_received ELSE 0 END) as received_on_time,
    SUM(CASE WHEN NOT is_on_time THEN quantity_received ELSE 0 END) as received_late,
    ROUND(
        100.0 * SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(*), 0),
        2
    ) as on_time_percentage
FROM deliveries
GROUP BY delivery_date
ORDER BY delivery_date;
