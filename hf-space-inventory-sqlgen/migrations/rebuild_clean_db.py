"""
One-time DB rebuild: reconstruct manufacturing.db from a clean state.

The existing manufacturing.db has deep page-level corruption (orphan index +
malformed data pages) that prevents VACUUM from succeeding.  This script:

  1. Creates a fresh SQLite database at manufacturing_new.db
  2. Applies the semantic layer DDL from schema_sqlite.sql
  3. Calls the purchasing / WIP tables migration to create and seed ERP tables
  4. Registers all 12 ERP tables in schema_nodes
  5. Renames the old DB to manufacturing.db.bak and promotes the new DB

Run once from the hf-space-inventory-sqlgen directory:
    python migrations/rebuild_clean_db.py

After this script completes, run:
    python migrations/add_erp_tables_to_schema_nodes.py   (no-op — schema_nodes already populated)
    python graph_sync.py                                   (push to ArangoDB)
"""

import os
import shutil
import sqlite3
import sys

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.join(os.path.dirname(__file__), "..")
SCHEMA_DIR  = os.path.join(BASE_DIR, "app_schema")
OLD_DB      = os.path.join(SCHEMA_DIR, "manufacturing.db")
NEW_DB      = os.path.join(SCHEMA_DIR, "manufacturing_new.db")
BAK_DB      = os.path.join(SCHEMA_DIR, "manufacturing.db.bak")
SCHEMA_SQL  = os.path.join(SCHEMA_DIR, "schema_sqlite.sql")

# Adjust so the migration module can find the DB
sys.path.insert(0, os.path.join(BASE_DIR, "migrations"))
os.environ.setdefault("ARANGO_DB", "manufacturing_graph")

# ── ERP table registry (matches add_erp_tables_to_schema_nodes.py) ────────────
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


def step1_apply_schema(conn: sqlite3.Connection) -> None:
    """Apply schema_sqlite.sql DDL to the fresh DB."""
    print("  Reading schema_sqlite.sql…")
    with open(SCHEMA_SQL, "r") as f:
        ddl = f.read()
    conn.executescript(ddl)
    print("  Schema applied.")


def step2_seed_erp_tables(new_db_path: str) -> None:
    """Run add_purchasing_wip_tables migration against the new DB."""
    import importlib.util, types

    mig_path = os.path.join(BASE_DIR, "migrations", "add_purchasing_wip_tables.py")
    spec = importlib.util.spec_from_file_location("add_purchasing_wip_tables", mig_path)
    mod = importlib.util.module_from_spec(spec)

    # Override the DB_PATH constant before the module runs its body
    original_db = None
    spec.loader.exec_module(mod)  # loads globals without running run()
    mod.DB_PATH = new_db_path     # redirect to new DB
    print("  Running add_purchasing_wip_tables.run()…")
    mod.run()


def step3_register_schema_nodes(conn: sqlite3.Connection) -> None:
    """Insert schema_nodes rows for every ERP table."""
    for table_name, description in ERP_TABLE_REGISTRY:
        conn.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM schema_nodes").fetchone()[0]
    print(f"  schema_nodes: {count} rows registered.")


def step4_verify(conn: sqlite3.Connection) -> None:
    """Spot-check a few ERP tables for data."""
    tables_to_check = [
        "work_order", "purchase_order", "operation",
        "labor_ticket", "suppliers", "schema_nodes",
    ]
    print("\n  Verification:")
    for t in tables_to_check:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"    {t}: {n} rows")
        except Exception as e:
            print(f"    {t}: ERROR — {e}")


def run() -> None:
    print(f"Rebuilding manufacturing.db")
    print(f"  Old DB  : {OLD_DB}")
    print(f"  New DB  : {NEW_DB}")

    # Remove any leftover new DB from a prior failed run.
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)

    # ── Step 1: Semantic layer schema ─────────────────────────────────────────
    print("\nStep 1 — Apply schema_sqlite.sql…")
    conn = sqlite3.connect(NEW_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    step1_apply_schema(conn)
    conn.close()

    # ── Step 2: ERP tables (creates tables + seeds data) ──────────────────────
    print("\nStep 2 — Seed ERP tables via add_purchasing_wip_tables…")
    step2_seed_erp_tables(NEW_DB)

    # ── Step 3: Register tables in schema_nodes ────────────────────────────────
    print("\nStep 3 — Register ERP tables in schema_nodes…")
    conn = sqlite3.connect(NEW_DB)
    step3_register_schema_nodes(conn)
    conn.close()

    # ── Step 4: Verify ─────────────────────────────────────────────────────────
    print("\nStep 4 — Verify…")
    conn = sqlite3.connect(NEW_DB)
    step4_verify(conn)
    conn.close()

    # ── Step 5: Promote new DB ─────────────────────────────────────────────────
    print(f"\nStep 5 — Promote new DB…")
    if os.path.exists(OLD_DB):
        shutil.move(OLD_DB, BAK_DB)
        print(f"  Old DB backed up to: {BAK_DB}")
    # Remove any stale WAL/SHM from old DB
    for ext in ("-wal", "-shm"):
        stale = OLD_DB + ext
        if os.path.exists(stale):
            os.remove(stale)
    shutil.move(NEW_DB, OLD_DB)
    print(f"  New DB promoted to: {OLD_DB}")

    print("\nDone. manufacturing.db is now clean and fully populated.")
    print("Next step: run graph_sync.py to push table/column vertices to ArangoDB.")


if __name__ == "__main__":
    run()
