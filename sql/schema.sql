-- Hypothetical aerospace manufacturing schema (Postgres)
CREATE SCHEMA IF NOT EXISTS pta;
SET search_path = pta;

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT,
  contact_email TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parts (
  part_id SERIAL PRIMARY KEY,
  part_number TEXT UNIQUE NOT NULL,
  description TEXT,
  unit_cost NUMERIC(12,4),
  supplier_id INTEGER REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assemblies (
  assembly_id SERIAL PRIMARY KEY,
  assembly_code TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assembly_parts (
  assembly_id INTEGER REFERENCES assemblies(assembly_id) ON DELETE CASCADE,
  part_id INTEGER REFERENCES parts(part_id) ON DELETE CASCADE,
  qty INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (assembly_id, part_id)
);

CREATE TABLE IF NOT EXISTS products (
  product_id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  assembly_id INTEGER REFERENCES assemblies(assembly_id),
  name TEXT,
  list_price NUMERIC(12,2),
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
  customer_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  industry TEXT,
  country TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  order_id SERIAL PRIMARY KEY,
  order_number TEXT UNIQUE NOT NULL,
  customer_id INTEGER REFERENCES customers(customer_id),
  order_date DATE,
  status TEXT,
  total_amount NUMERIC(14,2),
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
  order_item_id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(product_id),
  qty INTEGER NOT NULL,
  unit_price NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS machines (
  machine_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT,
  installed_at DATE
);

CREATE TABLE IF NOT EXISTS production_runs (
  run_id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(product_id),
  machine_id INTEGER REFERENCES machines(machine_id),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  quantity INTEGER,
  status TEXT
);

CREATE TABLE IF NOT EXISTS maintenance_records (
  maintenance_id SERIAL PRIMARY KEY,
  machine_id INTEGER REFERENCES machines(machine_id),
  performed_at TIMESTAMP,
  notes TEXT,
  cost NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS quality_checks (
  qc_id SERIAL PRIMARY KEY,
  run_id INTEGER REFERENCES production_runs(run_id) ON DELETE CASCADE,
  checked_at TIMESTAMP,
  passed BOOLEAN,
  defects_count INTEGER DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS shipments (
  shipment_id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(order_id) ON DELETE SET NULL,
  shipped_at TIMESTAMP,
  carrier TEXT,
  tracking_number TEXT
);

CREATE INDEX IF NOT EXISTS idx_parts_supplier ON parts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_assembly_parts_part ON assembly_parts(part_id);
CREATE INDEX IF NOT EXISTS idx_production_runs_product ON production_runs(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
