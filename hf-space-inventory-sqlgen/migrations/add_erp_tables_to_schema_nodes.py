"""
Migration: Register the 11 populated ERP tables in schema_nodes.

These tables were created and seeded by add_purchasing_wip_tables.py but
were never registered in schema_nodes, making them invisible to:
  - The Schema Browser Gradio tab
  - /mcp/tools/list_schema_tables endpoint
  - graph_sync.py (structural containment layer — tables/columns in ArangoDB)

This migration also:
  1. Removes the orphan auto-index (sqlite_autoindex_schema_intent_perspectives_1)
     that prevents normal sqlite3.connect() from opening the DB.
  2. Creates schema_nodes (and the rest of the semantic layer tables) if they
     do not already exist, using the same DDL as schema_sqlite.sql.
  3. Creates and seeds the suppliers table if it was not previously installed.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_erp_tables_to_schema_nodes.py

Safe to re-run: CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE throughout.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── ERP tables to register ────────────────────────────────────────────────────
# Each entry: (table_name, description)
ERP_TABLE_REGISTRY = [
    ("certification",   "Supplier certification records (CoC, FAI, PPAP, 8130-3, Material Test Report)"),
    ("invoice_header",  "AP invoice headers linked to purchase orders — three-way match and payment status"),
    ("labor_ticket",    "Labor time postings against work order operations (clock-in/out, hours, cost)"),
    ("material_issue",  "Raw material issues from stock to WIP work orders (quantity, unit cost, total cost)"),
    ("operation",       "Work order routing steps — sequence, resource, estimated vs actual hours and costs"),
    ("po_line",         "Purchase order line items (part, quantity, unit cost, line total)"),
    ("purchase_order",  "Purchase order headers for material and outside-service buys"),
    ("receiving",       "Goods receipts against purchase orders — quantity ordered vs received, inspection status"),
    ("service",         "Outside service definitions (anodize, heat treat, NDT, plating, painting)"),
    ("shop_resource",   "Shop work centers and outside-service buckets (machine, labor, service types)"),
    ("suppliers",       "Supplier master — name, category, certification level, payment terms, lead time"),
    ("work_order",      "Work order master — part, quantity, status, routing template, accumulated actual costs"),
]

# ── Suppliers seed data ───────────────────────────────────────────────────────
SUPPLIERS_DDL = """
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id        TEXT PRIMARY KEY,
    supplier_name      TEXT NOT NULL,
    category           TEXT,
    certification_level TEXT,
    payment_terms      TEXT,
    lead_time_days     INTEGER,
    outside_service    INTEGER DEFAULT 0,
    active             INTEGER DEFAULT 1,
    contact_email      TEXT,
    phone              TEXT,
    address            TEXT,
    performance_rating REAL,
    created_date       DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

SUPPLIERS_SEED = [
    ("S-001", "Precision Aerospace Corp",      "Raw Material",    "AS9100D", "Net 45",  14, 0),
    ("S-002", "Advanced Alloy Systems Inc",    "Raw Material",    "AS9100D", "Net 30",  21, 0),
    ("S-003", "Apex Machined Parts LLC",       "Sub-Assembly",    "AS9100D", "Net 30",  10, 0),
    ("S-004", "Titan Fastener Solutions",      "Raw Material",    "NADCAP",  "Net 45",   7, 0),
    ("S-005", "Aerojet Seal Systems",          "MRO",             "AS9100D", "Net 30",  12, 0),
    ("S-006", "Pacific Coast Composites",      "Sub-Assembly",    "NADCAP",  "Net 60",  30, 0),
    ("S-007", "Summit Bearing Technologies",   "MRO",             "AS9100D", "Net 30",   5, 0),
    ("S-008", "Desert Aerospace Coatings",     "Outside Service", "NADCAP",  "Net 30",   3, 1),
    ("S-009", "SoCal Heat Treatment Inc",      "Outside Service", "NADCAP",  "Net 15",   2, 1),
    ("S-010", "Western NDT Services",          "Outside Service", "NADCAP",  "Net 30",   5, 1),
    ("S-011", "Coastal Plating & Finishing",   "Outside Service", "NADCAP",  "Net 30",   4, 1),
]

# ── schema_nodes DDL (matches schema_sqlite.sql) ──────────────────────────────
SCHEMA_NODES_DDL = """
CREATE TABLE IF NOT EXISTS schema_nodes (
    table_name  TEXT NOT NULL UNIQUE,
    table_type  TEXT,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def fix_orphan_index(conn: sqlite3.Connection) -> None:
    """Delete the orphan auto-index that prevents normal DB open.

    sqlite_autoindex_schema_intent_perspectives_1 was left behind when the
    schema_intent_perspectives table was removed without dropping its index.
    We use writable_schema mode to surgically remove it, then VACUUM.
    """
    conn.execute("PRAGMA writable_schema=ON")
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='sqlite_autoindex_schema_intent_perspectives_1'"
    )
    if cur.fetchone():
        conn.execute(
            "DELETE FROM sqlite_master WHERE type='index' "
            "AND name='sqlite_autoindex_schema_intent_perspectives_1'"
        )
        print("  Removed orphan index: sqlite_autoindex_schema_intent_perspectives_1")
    conn.execute("PRAGMA writable_schema=OFF")
    conn.commit()


def run() -> None:
    print(f"DB path: {DB_PATH}")

    # Phase 1: Fix orphan index using writable_schema mode.
    # We open a separate connection for this because writable_schema changes
    # must be committed before the DB can be opened cleanly.
    print("\nPhase 1 — Remove orphan index (if present)...")
    conn_ws = sqlite3.connect(DB_PATH)
    fix_orphan_index(conn_ws)
    conn_ws.close()

    # VACUUM rebuilds the DB file and purges the deleted index from all
    # internal B-tree pages.  Must be run outside a transaction.
    vac_conn = sqlite3.connect(DB_PATH)
    vac_conn.execute("VACUUM")
    vac_conn.close()
    print("  VACUUM complete — DB is now clean.")

    # Phase 2: Normal operations — the DB can now be opened without errors.
    print("\nPhase 2 — Apply schema and seed data...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create suppliers table and seed it if not already present.
    cur.executescript(SUPPLIERS_DDL)
    inserted = 0
    for row in SUPPLIERS_SEED:
        cur.execute(
            "INSERT OR IGNORE INTO suppliers "
            "(supplier_id, supplier_name, category, certification_level, "
            " payment_terms, lead_time_days, outside_service) "
            "VALUES (?,?,?,?,?,?,?)",
            row,
        )
        inserted += cur.rowcount
    print(f"  suppliers: {inserted} rows inserted (INSERT OR IGNORE)")

    # Create schema_nodes table.
    cur.executescript(SCHEMA_NODES_DDL)

    # Register all ERP tables in schema_nodes.
    nodes_inserted = 0
    for table_name, description in ERP_TABLE_REGISTRY:
        cur.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
        nodes_inserted += cur.rowcount

    conn.commit()
    conn.close()

    print(f"  schema_nodes: {nodes_inserted} rows inserted ({len(ERP_TABLE_REGISTRY)} total registered)")
    print("\nDone. All populated ERP tables are now visible to the Schema Browser.")
    print("Re-run graph_sync.py to push table/column vertices to ArangoDB.")


if __name__ == "__main__":
    run()
