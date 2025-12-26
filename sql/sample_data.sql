-- Sample data for Product On-Time Analysis Database
-- Provides test data for suppliers, parts, assemblies, products, deliveries, and production runs

-- Insert sample suppliers
INSERT INTO suppliers (supplier_name, supplier_code, country, contact_email) VALUES
    ('Apex Components Inc', 'APX-001', 'USA', 'orders@apexcomp.com'),
    ('Global Parts Supply', 'GPS-002', 'China', 'sales@globalparts.cn'),
    ('European Manufacturing', 'EUM-003', 'Germany', 'contact@euromanuf.de'),
    ('Pacific Precision', 'PAC-004', 'Japan', 'info@pacificprecision.jp'),
    ('American Steel Works', 'ASW-005', 'USA', 'sales@amsteelworks.com')
ON CONFLICT (supplier_code) DO NOTHING;

-- Insert sample parts
INSERT INTO parts (part_number, part_name, supplier_id, unit_cost, lead_time_days) VALUES
    ('PN-1001', 'Titanium Alloy Plate', 1, 125.50, 14),
    ('PN-1002', 'Carbon Fiber Sheet', 2, 89.99, 21),
    ('PN-1003', 'Precision Bearing', 4, 45.75, 10),
    ('PN-1004', 'Hydraulic Cylinder', 3, 210.00, 28),
    ('PN-1005', 'Electronic Control Unit', 2, 350.00, 35),
    ('PN-1006', 'Aluminum Extrusion', 5, 32.50, 7),
    ('PN-1007', 'Stainless Steel Fasteners', 1, 12.99, 5),
    ('PN-1008', 'Composite Panel', 2, 165.00, 21),
    ('PN-1009', 'Servo Motor', 4, 425.00, 42),
    ('PN-1010', 'Pressure Sensor', 3, 78.50, 14)
ON CONFLICT (part_number) DO NOTHING;

-- Insert sample products
INSERT INTO products (product_code, product_name, product_family, target_cycle_time_hours) VALUES
    ('PROD-A100', 'Wing Assembly Alpha', 'Aircraft Components', 48),
    ('PROD-A200', 'Fuselage Section Beta', 'Aircraft Components', 72),
    ('PROD-B100', 'Landing Gear Assembly', 'Landing Systems', 36),
    ('PROD-C100', 'Avionics Control Panel', 'Electronics', 24),
    ('PROD-D100', 'Engine Mount Assembly', 'Engine Systems', 40)
ON CONFLICT (product_code) DO NOTHING;

-- Insert sample assemblies (bill of materials)
INSERT INTO assemblies (product_id, part_id, quantity_required) VALUES
    -- Wing Assembly Alpha (PROD-A100)
    (1, 1, 4),  -- Titanium Alloy Plate
    (1, 2, 8),  -- Carbon Fiber Sheet
    (1, 6, 12), -- Aluminum Extrusion
    (1, 7, 200), -- Stainless Steel Fasteners
    -- Fuselage Section Beta (PROD-A200)
    (2, 1, 6),  -- Titanium Alloy Plate
    (2, 6, 20), -- Aluminum Extrusion
    (2, 7, 350), -- Stainless Steel Fasteners
    (2, 8, 10), -- Composite Panel
    -- Landing Gear Assembly (PROD-B100)
    (3, 3, 8),  -- Precision Bearing
    (3, 4, 2),  -- Hydraulic Cylinder
    (3, 7, 100), -- Stainless Steel Fasteners
    (3, 10, 4), -- Pressure Sensor
    -- Avionics Control Panel (PROD-C100)
    (4, 5, 3),  -- Electronic Control Unit
    (4, 9, 2),  -- Servo Motor
    (4, 10, 6), -- Pressure Sensor
    -- Engine Mount Assembly (PROD-D100)
    (5, 1, 2),  -- Titanium Alloy Plate
    (5, 6, 8),  -- Aluminum Extrusion
    (5, 7, 150) -- Stainless Steel Fasteners
ON CONFLICT (product_id, part_id) DO NOTHING;

-- Insert sample deliveries (August 2025)
INSERT INTO deliveries (part_id, delivery_date, quantity_received, quantity_expected, days_late) VALUES
    -- Week 1
    (1, '2025-08-01', 100, 100, 0),
    (2, '2025-08-01', 200, 200, 0),
    (3, '2025-08-01', 150, 150, 2),
    (7, '2025-08-02', 5000, 5000, 0),
    (6, '2025-08-02', 300, 300, -1),
    (4, '2025-08-03', 50, 50, 5),
    (5, '2025-08-03', 80, 100, 7),
    -- Week 2
    (1, '2025-08-05', 120, 120, 0),
    (8, '2025-08-05', 100, 100, 0),
    (9, '2025-08-06', 40, 50, 10),
    (10, '2025-08-06', 200, 200, 0),
    (2, '2025-08-07', 180, 200, 3),
    (3, '2025-08-08', 160, 160, 0),
    (6, '2025-08-09', 280, 300, 1),
    -- Week 3
    (7, '2025-08-12', 6000, 6000, 0),
    (1, '2025-08-12', 110, 110, 0),
    (4, '2025-08-13', 45, 50, 8),
    (5, '2025-08-14', 90, 100, 5),
    (8, '2025-08-14', 95, 100, 2),
    (9, '2025-08-15', 48, 50, 6)
ON CONFLICT DO NOTHING;

-- Insert sample production runs (August 2025)
INSERT INTO production_runs (product_id, run_date, quantity_produced, quantity_defective) VALUES
    -- Wing Assembly Alpha
    (1, '2025-08-01', 12, 0),
    (1, '2025-08-03', 15, 1),
    (1, '2025-08-05', 14, 0),
    (1, '2025-08-08', 13, 1),
    (1, '2025-08-10', 16, 0),
    (1, '2025-08-12', 15, 1),
    (1, '2025-08-15', 14, 0),
    -- Fuselage Section Beta
    (2, '2025-08-02', 8, 0),
    (2, '2025-08-06', 10, 1),
    (2, '2025-08-09', 9, 0),
    (2, '2025-08-13', 10, 1),
    -- Landing Gear Assembly
    (3, '2025-08-01', 20, 1),
    (3, '2025-08-04', 22, 0),
    (3, '2025-08-07', 21, 1),
    (3, '2025-08-11', 23, 2),
    (3, '2025-08-14', 20, 0),
    -- Avionics Control Panel
    (4, '2025-08-02', 30, 1),
    (4, '2025-08-05', 32, 2),
    (4, '2025-08-08', 28, 1),
    (4, '2025-08-12', 31, 1),
    (4, '2025-08-15', 29, 0),
    -- Engine Mount Assembly
    (5, '2025-08-03', 18, 1),
    (5, '2025-08-07', 20, 0),
    (5, '2025-08-10', 19, 1),
    (5, '2025-08-14', 21, 0)
ON CONFLICT DO NOTHING;

-- Insert sample quality metrics
INSERT INTO quality_metrics (run_id, metric_name, metric_value, measured_at) VALUES
    (1, 'Surface Finish Quality', 9.5, '2025-08-01 14:30:00'),
    (1, 'Dimensional Accuracy', 0.002, '2025-08-01 14:35:00'),
    (2, 'Surface Finish Quality', 9.2, '2025-08-03 15:00:00'),
    (2, 'Dimensional Accuracy', 0.003, '2025-08-03 15:05:00'),
    (8, 'Structural Integrity', 98.5, '2025-08-02 16:00:00'),
    (8, 'Weld Quality Score', 9.7, '2025-08-02 16:15:00'),
    (12, 'Hydraulic Pressure Test', 100.0, '2025-08-01 13:00:00'),
    (12, 'Bearing Tolerance', 0.001, '2025-08-01 13:15:00')
ON CONFLICT DO NOTHING;
