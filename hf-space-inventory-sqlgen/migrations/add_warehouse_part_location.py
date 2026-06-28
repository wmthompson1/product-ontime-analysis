"""
Migration: add the WAREHOUSE and PART_LOCATION stand-in tables.

These two tables complete the inventory-transaction reconciliation surface so the
ground-truth review query (docs/my-mrp-kb/kb-inventory-transactions/
Inventory_-_Transactions_AI_Review.sql) can run as a SQLite synthetic benchmark.
They mirror the real Infor VISUAL DDLs in this repo (ddl/dbo.WAREHOUSE.sql,
ddl/dbo.PART_LOCATION.sql), trimmed to the columns the reconciliation needs.

New tables (declared FKs so the metadata exporter can mint structural edges):
  - warehouse       (WAREHOUSE — physical stocking location, belongs to a site)
  - part_location   (PART_LOCATION — on-hand qty of a part at a warehouse location)

Synthetic data is DETERMINISTIC and GROUNDED to the existing ledger:
  - 2 warehouses per site (Main Stores + Floor Stock), 6 total.
  - On-hand per (part, site) = the inventory_transaction net effect
    (SUM CASE type='I' -> +qty ELSE -qty) when that net is positive, so the
    on-hand axis reconciles with the ledger; otherwise it falls back to the
    part master on_hand_qty snapshot (a realistic positive value that surfaces a
    genuine ledger-vs-floor discrepancy). No randomness.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_warehouse_part_location.py

Safe to re-run: CREATE TABLE IF NOT EXISTS; warehouse seed uses INSERT OR IGNORE
(stable IDs); part_location seed is skipped if the table already has rows;
schema_nodes registration uses INSERT OR IGNORE.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── New table DDL (declared FKs, mirrors the real VISUAL DDLs) ─────────────────
DDL = """
-- Physical stocking location, belongs to a site (mirrors WAREHOUSE)
CREATE TABLE IF NOT EXISTS warehouse (
    warehouse_id TEXT PRIMARY KEY,                 -- WAREHOUSE.ID
    description  TEXT,                              -- WAREHOUSE.DESCRIPTION
    name         TEXT,                              -- WAREHOUSE.NAME
    site_id      TEXT NOT NULL,                     -- WAREHOUSE.SITE_ID
    region_id    TEXT,                              -- WAREHOUSE.REGION_ID
    independent  TEXT NOT NULL DEFAULT 'Y',         -- WAREHOUSE.INDEPENDENT
    mrp_exempt   TEXT NOT NULL DEFAULT 'N',         -- WAREHOUSE.MRP_EXEMPT
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

-- On-hand quantity of a part at a warehouse location (mirrors PART_LOCATION)
CREATE TABLE IF NOT EXISTS part_location (
    part_location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id       TEXT NOT NULL,                    -- PART_LOCATION.PART_ID
    warehouse_id  TEXT NOT NULL,                    -- PART_LOCATION.WAREHOUSE_ID
    location_id   TEXT NOT NULL DEFAULT 'STORES',   -- PART_LOCATION.LOCATION_ID
    description   TEXT,                             -- PART_LOCATION.DESCRIPTION
    qty           REAL NOT NULL DEFAULT 0,          -- PART_LOCATION.QTY (on-hand)
    committed_qty REAL NOT NULL DEFAULT 0,          -- PART_LOCATION.COMMITTED_QTY
    status        TEXT NOT NULL DEFAULT 'A',        -- PART_LOCATION.STATUS (A=active)
    last_count_date DATE,                           -- PART_LOCATION.LAST_COUNT_DATE
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (part_id, warehouse_id, location_id),
    FOREIGN KEY (part_id)      REFERENCES part(part_id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id)
);
"""

# ── schema_nodes registry entries for the new tables ──────────────────────────
REGISTRY = [
    ("warehouse",     "Physical stocking location (warehouse) belonging to a site — anchors part on-hand"),
    ("part_location", "On-hand quantity of a part at a warehouse location — physical inventory snapshot for reconciliation"),
]

SCHEMA_NODES_DDL = """
CREATE TABLE IF NOT EXISTS schema_nodes (
    table_name  TEXT NOT NULL UNIQUE,
    table_type  TEXT,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

NEW_TABLES = [r[0] for r in REGISTRY]

# Tables this migration reads from when grounding the synthetic on-hand. They are
# created/seeded earlier (schema_sqlite.sql + Wave 4 migration + ERP seeder), so a
# clear preflight error beats a cryptic FK / "no such table" failure if run early.
PREREQUISITE_TABLES = ["site", "part", "inventory_transaction"]


def preflight(cur: sqlite3.Cursor) -> None:
    present = {
        r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = [t for t in PREREQUISITE_TABLES if t not in present]
    if missing:
        raise SystemExit(
            "Preflight failed — required tables missing: "
            f"{', '.join(missing)}. Run the schema/ERP/Wave 4 setup first."
        )


def seed_warehouses(cur: sqlite3.Cursor) -> None:
    """2 warehouses per site (Main Stores + Floor Stock). Stable IDs, idempotent."""
    sites = cur.execute("SELECT site_id, site_name, region FROM site ORDER BY site_id").fetchall()
    rows = []
    for site_id, site_name, region in sites:
        # site_id looks like 'SITE-1' -> suffix '1'
        suffix = str(site_id).split("-")[-1]
        rows.append((f"WH-{suffix}A", f"Main Stores — {site_name}", f"{site_id} Main Stores",
                     site_id, region, "Y", "N"))
        rows.append((f"WH-{suffix}B", f"Floor Stock / WIP — {site_name}", f"{site_id} Floor Stock",
                     site_id, region, "N", "N"))
    cur.executemany(
        "INSERT OR IGNORE INTO warehouse "
        "(warehouse_id, description, name, site_id, region_id, independent, mrp_exempt) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    print(f"  warehouse: {cur.rowcount} rows inserted ({len(rows)} attempted)")


def main_warehouse_for_site(cur: sqlite3.Cursor, site_id: str) -> str:
    """Return the 'Main Stores' warehouse id for a site (WH-<suffix>A)."""
    suffix = str(site_id).split("-")[-1]
    return f"WH-{suffix}A"


def seed_part_locations(cur: sqlite3.Cursor) -> None:
    """On-hand per (part, site) grounded to the ledger net effect (positive),
    else the part master on_hand_qty snapshot. Skipped if already seeded."""
    existing = cur.execute("SELECT COUNT(*) FROM part_location").fetchone()[0]
    if existing:
        print(f"  part_location: already {existing} rows — skipping seed")
        return

    # Net ledger effect + last activity date per (part, site)
    agg = cur.execute(
        """
        SELECT part_id,
               site_id,
               SUM(CASE WHEN type='I' THEN quantity ELSE -quantity END) AS net_effect,
               MAX(trans_date) AS last_date
        FROM inventory_transaction
        WHERE site_id IS NOT NULL
        GROUP BY part_id, site_id
        """
    ).fetchall()

    part_desc = dict(cur.execute("SELECT part_id, part_description FROM part").fetchall())
    part_oh = dict(cur.execute("SELECT part_id, on_hand_qty FROM part").fetchall())

    rows = []
    for part_id, site_id, net_effect, last_date in agg:
        net_effect = net_effect or 0.0
        if net_effect > 0:
            on_hand = round(net_effect, 4)            # grounded: reconciles with ledger
        else:
            on_hand = round(float(part_oh.get(part_id) or 0.0), 4)  # realistic snapshot -> discrepancy
        wh = main_warehouse_for_site(cur, site_id)
        rows.append((part_id, wh, "STORES", part_desc.get(part_id), on_hand, 0.0, "A", last_date))

    cur.executemany(
        "INSERT OR IGNORE INTO part_location "
        "(part_id, warehouse_id, location_id, description, qty, committed_qty, status, last_count_date) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    print(f"  part_location: {cur.rowcount} rows inserted ({len(rows)} attempted)")


def run() -> None:
    print(f"DB path: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    preflight(cur)

    print("\nPhase 1 — create tables...")
    cur.executescript(DDL)
    for t in NEW_TABLES:
        print(f"  staged: {t}")

    print("\nPhase 2 — seed warehouses...")
    seed_warehouses(cur)

    print("\nPhase 3 — seed part_location (grounded to the ledger)...")
    seed_part_locations(cur)

    print("\nPhase 4 — register in schema_nodes...")
    cur.executescript(SCHEMA_NODES_DDL)
    registered = 0
    for table_name, description in REGISTRY:
        cur.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
        registered += cur.rowcount

    conn.commit()

    # Verify — counts + declared FKs the exporter would mint
    print("\nVerification:")
    for t in NEW_TABLES:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")
        cur.execute(f"PRAGMA foreign_key_list({t})")
        for fk in cur.fetchall():
            print(f"    FK {t}.{fk[3]} -> {fk[2]}.{fk[4]}")
    print(f"  {registered} tables registered in schema_nodes")
    conn.close()
    print("\nDone. warehouse + part_location are present and grounded.")


if __name__ == "__main__":
    run()
