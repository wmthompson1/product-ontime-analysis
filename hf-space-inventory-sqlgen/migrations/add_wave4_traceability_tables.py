"""
Migration: Plan 8 · Wave 4 — Synthetic ERP Expansion (Traceability Spine).

Stages the 8 new synthetic ERP tables for manufacturing / warranty traceability
and rebuilds `suppliers` to add a declared PRIMARY KEY.  All new tables carry
DECLARED foreign-key constraints so the metadata exporter
(replit_integrations/export_graph_metadata.py) mints the structural `references`
edges automatically from PRAGMA foreign_key_list — no convention-guessing.

New tables (mirroring the real Infor VISUAL DDLs in this repo):
  - site                   (dimension; anchors orphan site_id)
  - inventory_transaction  (INVENTORY_TRANS — R/A/I x I/O movement ledger)
  - trace                  (TRACE — a traced lot/serial of a part)
  - trace_inventory_trace  (TRACE_INV_TRANS — bridge: trace lot <-> transaction)
  - inv_trans_dist         (INV_TRANS_DIST — genealogy: IN-trans <-> OUT-trans)
  - customer_order         (CUSTOMER_ORDER — demand header)
  - customer_order_line    (CUST_ORDER_LINE — demand detail)
  - payable_line           (RECEIVABLE_LINE / VR_PAYABLE_DET — AP detail)

Design: surrogate single-column <entity>_id PKs + declared FKs (Plan 8 Wave 4).

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_wave4_traceability_tables.py

Safe to re-run: suppliers rebuild is guarded by a PK check; new tables use
CREATE TABLE IF NOT EXISTS; schema_nodes registration uses INSERT OR IGNORE.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── New Wave 4 table DDL (declared FKs, surrogate <entity>_id PKs) ─────────────
WAVE4_DDL = """
-- Site dimension (anchors orphan site_id across the ERP)
CREATE TABLE IF NOT EXISTS site (
    site_id    TEXT PRIMARY KEY,
    site_name  TEXT NOT NULL,
    region     TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Inventory movement ledger (mirrors INVENTORY_TRANS; R/A/I x I/O)
CREATE TABLE IF NOT EXISTS inventory_transaction (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class      TEXT NOT NULL CHECK(class IN ('R','A','I')),   -- Released / Adjust / Issue
    type       TEXT NOT NULL CHECK(type  IN ('I','O')),       -- In / Out (effect on QOH)
    part_id    TEXT NOT NULL,
    wo_id      TEXT,
    po_id      TEXT,
    site_id    TEXT,
    quantity   REAL NOT NULL,
    trans_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES part(part_id),
    FOREIGN KEY (wo_id)   REFERENCES work_order(wo_id),
    FOREIGN KEY (po_id)   REFERENCES purchase_order(po_id),
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

-- Traced lot / serial of a part (mirrors TRACE)
CREATE TABLE IF NOT EXISTS trace (
    trace_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id         TEXT NOT NULL,
    lot_id          TEXT,
    serial_id       TEXT,
    in_qty          REAL DEFAULT 0,
    out_qty         REAL DEFAULT 0,
    production_date DATE,
    expiration_date DATE,
    site_id         TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES part(part_id),
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

-- Bridge: trace lot <-> inventory transaction (mirrors TRACE_INV_TRANS)
CREATE TABLE IF NOT EXISTS trace_inventory_trace (
    trace_inv_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id        TEXT NOT NULL,
    trace_id       INTEGER NOT NULL,
    transaction_id INTEGER NOT NULL,
    qty            REAL NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id)        REFERENCES part(part_id),
    FOREIGN KEY (trace_id)       REFERENCES trace(trace_id),
    FOREIGN KEY (transaction_id) REFERENCES inventory_transaction(transaction_id)
);

-- Genealogy / depth driver: IN-trans <-> OUT-trans (mirrors INV_TRANS_DIST)
CREATE TABLE IF NOT EXISTS inv_trans_dist (
    dist_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    in_trans_id  INTEGER NOT NULL,
    out_trans_id INTEGER NOT NULL,
    dist_qty     REAL NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (in_trans_id)  REFERENCES inventory_transaction(transaction_id),
    FOREIGN KEY (out_trans_id) REFERENCES inventory_transaction(transaction_id)
);

-- Customer order header (mirrors CUSTOMER_ORDER)
CREATE TABLE IF NOT EXISTS customer_order (
    order_id      TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    order_date    DATE NOT NULL,
    site_id       TEXT,
    status        TEXT DEFAULT 'Open' CHECK(status IN ('Open','Shipped','Closed','Cancelled')),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

-- Customer order line (mirrors CUST_ORDER_LINE)
CREATE TABLE IF NOT EXISTS customer_order_line (
    order_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      TEXT NOT NULL,
    line_no       INTEGER NOT NULL,
    part_id       TEXT NOT NULL,
    site_id       TEXT,
    order_qty     REAL NOT NULL,
    unit_price    REAL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES customer_order(order_id),
    FOREIGN KEY (part_id)  REFERENCES part(part_id),
    FOREIGN KEY (site_id)  REFERENCES site(site_id)
);

-- AP payable detail; extends the existing invoice_header (mirrors RECEIVABLE_LINE)
CREATE TABLE IF NOT EXISTS payable_line (
    payable_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL,
    line_no         INTEGER NOT NULL,
    po_id           TEXT,
    part_id         TEXT,
    qty             REAL,
    amount          REAL NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoice_header(invoice_id),
    FOREIGN KEY (po_id)      REFERENCES purchase_order(po_id),
    FOREIGN KEY (part_id)    REFERENCES part(part_id)
);
"""

# ── schema_nodes registry entries for the new tables ──────────────────────────
WAVE4_REGISTRY = [
    ("site",                  "Site dimension — physical plant / location anchoring inventory, orders, and work orders"),
    ("inventory_transaction", "Inventory movement ledger (CLASS R/A/I x TYPE I/O) — receipts, issues, adjustments"),
    ("trace",                 "Traced lot / serial record of a part — production and expiration dates, quantities"),
    ("trace_inventory_trace", "Bridge linking a trace lot to an inventory transaction (qty-weighted) for genealogy"),
    ("inv_trans_dist",        "Inventory transaction distribution — links an IN movement to an OUT movement (lot genealogy)"),
    ("customer_order",        "Customer order header — demand-side sales orders with site and status"),
    ("customer_order_line",   "Customer order line items — part, quantity, unit price per order"),
    ("payable_line",          "AP payable line detail extending invoice_header — part, PO, quantity, amount"),
]

SCHEMA_NODES_DDL = """
CREATE TABLE IF NOT EXISTS schema_nodes (
    table_name  TEXT NOT NULL UNIQUE,
    table_type  TEXT,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

WAVE4_TABLES = [r[0] for r in WAVE4_REGISTRY]


def suppliers_has_pk(cur: sqlite3.Cursor) -> bool:
    cur.execute("PRAGMA table_info(suppliers)")
    return any(col[5] for col in cur.fetchall())  # col[5] == pk flag


def rebuild_suppliers_with_pk(conn: sqlite3.Connection) -> None:
    """Rebuild `suppliers` adding a TEXT PRIMARY KEY on supplier_id.

    Preserves all existing columns, defaults, and data.  supplier_id is forced
    to TEXT (values are 'S-001'-style strings) and made the primary key.
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(suppliers)")
    info = cur.fetchall()  # (cid, name, type, notnull, dflt_value, pk)

    col_defs = []
    col_names = []
    for _cid, name, ctype, notnull, dflt, _pk in info:
        col_names.append(name)
        if name == "supplier_id":
            col_defs.append("supplier_id TEXT PRIMARY KEY")
            continue
        piece = f"{name} {ctype or 'TEXT'}"
        if notnull:
            piece += " NOT NULL"
        if dflt is not None:
            piece += f" DEFAULT {dflt}"
        col_defs.append(piece)

    cols_sql = ",\n        ".join(col_defs)
    col_list = ", ".join(col_names)

    conn.execute("PRAGMA foreign_keys=OFF")
    cur.executescript(
        f"""
        DROP TABLE IF EXISTS suppliers_new;
        CREATE TABLE suppliers_new (
        {cols_sql}
        );
        INSERT INTO suppliers_new ({col_list}) SELECT {col_list} FROM suppliers;
        DROP TABLE suppliers;
        ALTER TABLE suppliers_new RENAME TO suppliers;
        """
    )
    conn.execute("PRAGMA foreign_keys=ON")
    print("  suppliers: rebuilt with PRIMARY KEY (supplier_id TEXT)")


def run() -> None:
    print(f"DB path: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    # Phase 1 — suppliers PK
    print("\nPhase 1 — suppliers primary key...")
    if suppliers_has_pk(cur):
        print("  suppliers already has a primary key — skipping rebuild.")
    else:
        rebuild_suppliers_with_pk(conn)

    # Phase 2 — create Wave 4 tables
    print("\nPhase 2 — create Wave 4 tables...")
    cur.executescript(WAVE4_DDL)
    for t in WAVE4_TABLES:
        print(f"  staged: {t}")

    # Phase 3 — register in schema_nodes
    print("\nPhase 3 — register in schema_nodes...")
    cur.executescript(SCHEMA_NODES_DDL)
    registered = 0
    for table_name, description in WAVE4_REGISTRY:
        cur.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
        registered += cur.rowcount

    conn.commit()

    # Verify — report declared FKs the exporter will mint
    print("\nVerification — declared foreign keys per new table:")
    total_fks = 0
    for t in WAVE4_TABLES:
        cur.execute(f"PRAGMA foreign_key_list({t})")
        fks = cur.fetchall()
        total_fks += len(fks)
        for fk in fks:
            # fk: (id, seq, table, from, to, on_update, on_delete, match)
            print(f"  {t}.{fk[3]} -> {fk[2]}.{fk[4]}")
    print(f"\n  {registered} tables registered in schema_nodes")
    print(f"  {total_fks} declared FK edges across {len(WAVE4_TABLES)} new tables")
    conn.close()
    print("\nM1 complete. Next: M2 seeder, then re-run export_graph_metadata.py.")


if __name__ == "__main__":
    run()
