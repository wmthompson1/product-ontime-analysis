-- Small sample dataset to validate schema quickly
INSERT INTO pta.suppliers (name, country, contact_email)
VALUES ('AeroFast Supplies', 'USA', 'contact@aerofast.example'),
       ('Orbital Parts Co', 'UK', 'sales@orbital.example')
ON CONFLICT DO NOTHING;

INSERT INTO pta.parts (part_number, description, unit_cost, supplier_id)
VALUES ('P-1001', 'Titanium bolt', 2.50, 1),
       ('P-1002', 'Composite panel', 120.00, 2),
       ('P-2001', 'Bearing assembly', 55.00, 1)
ON CONFLICT DO NOTHING;

INSERT INTO pta.assemblies (assembly_code, description)
VALUES ('A-01', 'Wing subassembly'),
       ('A-02', 'Fuselage section')
ON CONFLICT DO NOTHING;

INSERT INTO pta.assembly_parts (assembly_id, part_id, qty)
VALUES (1, 1, 20),
       (1, 2, 2),
       (2, 3, 10)
ON CONFLICT DO NOTHING;

INSERT INTO pta.products (sku, assembly_id, name, list_price)
VALUES ('SKU-W-01', 1, 'Wing Module', 15000.00),
       ('SKU-F-01', 2, 'Fuselage Module', 45000.00)
ON CONFLICT DO NOTHING;

INSERT INTO pta.customers (name, industry, country)
VALUES ('Skyline Air', 'Airlines', 'USA')
ON CONFLICT DO NOTHING;

INSERT INTO pta.orders (order_number, customer_id, order_date, status, total_amount)
VALUES ('ORD-1001', 1, '2025-10-01', 'confirmed', 60000.00)
ON CONFLICT DO NOTHING;

INSERT INTO pta.order_items (order_id, product_id, qty, unit_price)
VALUES (1, 1, 2, 15000.00),
       (1, 2, 1, 45000.00)
ON CONFLICT DO NOTHING;

INSERT INTO pta.machines (name, location, installed_at)
VALUES ('CNC-01', 'Plant A', '2023-01-15'),
       ('Press-02', 'Plant A', '2022-06-20')
ON CONFLICT DO NOTHING;

INSERT INTO pta.production_runs (product_id, machine_id, start_time, end_time, quantity, status)
VALUES (1, 1, now() - interval '10 days', now() - interval '9 days', 2, 'complete')
ON CONFLICT DO NOTHING;

INSERT INTO pta.quality_checks (run_id, checked_at, passed, defects_count, notes)
VALUES (1, now() - interval '9 days', TRUE, 0, 'Good')
ON CONFLICT DO NOTHING;

INSERT INTO pta.shipments (order_id, shipped_at, carrier, tracking_number)
VALUES (1, now() - interval '8 days', 'AeroShip', 'TRK123456')
ON CONFLICT DO NOTHING;
