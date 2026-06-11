"""
Migration: Add the operation_type lookup table and stamp the synthetic
operation rows with an operation_type_id so they can be queried and grouped by
the *kind* of operation (CNC, Paint, NDT, Inspect, Assembly, …).

What this does (all additive, safe to re-run):
  1. CREATE TABLE IF NOT EXISTS operation_type — the closed reference set of
     operation "kinds" (mirrors the private SQL Server OPERATION_TYPE
     (ID, DESCRIPTION, RESOURCE_ID) model).
  2. Seed operation_type with the full taxonomy (INSERT OR IGNORE).
  3. Add operation.operation_type_id (TEXT) if the column is missing.
  4. Backfill operation_type_id for every operation row that does not yet have
     one, derived from the row's resource_id (and service_id for OUTSIDE rows).

Idempotency:
  - The lookup uses INSERT OR IGNORE.
  - The column add is guarded by a PRAGMA table_info check.
  - The backfill only touches rows WHERE operation_type_id IS NULL, so re-running
    never reclassifies a row that already has a type.

The seed taxonomy below is kept identical to the operation_type seed block in
app_schema/schema_sqlite.sql (which covers fresh databases). This migration is
the path that stamps the *committed* manufacturing.db.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_operation_type.py

Safe to re-run.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── Operation-type taxonomy ───────────────────────────────────────────────────
# (operation_type_id, description, category, resource_id, active)
# Identical to the seed block in app_schema/schema_sqlite.sql.
OPERATION_TYPES = [
    ("CNC",      "CNC Milling",                   "Machining",         "CNC-MILL-1",   1),
    ("TURN",     "CNC Turning / Lathe",           "Machining",         "LATHE-1",      1),
    ("WJET",     "Waterjet Cutting",              "Machining",         "MC-006",       1),
    ("DEBURR",   "Deburr / Finishing",            "Finishing",         "DRILL-PRESS",  1),
    ("WELD",     "Welding",                       "Fabrication",       "WELD-A",       1),
    ("ASSY",     "Assembly",                      "Assembly",          "ASSEM-LINE-1", 1),
    ("INSPECT",  "In-Process Inspection / CMM",   "Quality",           "INSPECT-CMM",  1),
    ("FINSP",    "Final Inspection",              "Quality",           "LB-004",       1),
    ("NDT",      "Non-Destructive Test",          "Quality",           "SV-003",       1),
    ("REVIEW",   "Engineering / Planning Review", "Engineering",       None,           1),
    ("ANOD",     "Anodize",                       "Outside Finishing", "SV-001",       1),
    ("CHEM",     "Chemical Film",                 "Outside Finishing", "SV-004",       1),
    ("HTRT",     "Heat Treat",                    "Outside Process",   "SV-002",       1),
    ("PLATE",    "Plating",                       "Outside Finishing", "OUTSIDE",      1),
    ("PAINT",    "Paint / Prime",                 "Outside Finishing", "SV-005",       1),
    ("PARTMARK", "Part Marking / Etch",           "Finishing",         "DRILL-PRESS",  1),
]

# ── Work center → operation type (for non-OUTSIDE resources) ───────────────────
# Covers both seeders' vocabularies (add_purchasing_wip_tables.py: CNC-MILL-*,
# WELD-*, INSPECT-CMM, ASSEM-LINE-*, LATHE-1, DRILL-PRESS, OUTSIDE;
# seed_erp_synthetic.py: MC-*, LB-*, SV-*).
RESOURCE_TO_TYPE = {
    "CNC-MILL-1": "CNC", "CNC-MILL-2": "CNC", "MC-001": "CNC", "MC-003": "CNC",
    "DRILL-PRESS": "CNC", "LB-001": "CNC", "LB-002": "CNC",
    "MC-002": "TURN", "MC-004": "TURN", "MC-005": "TURN", "LATHE-1": "TURN",
    "MC-006": "WJET",
    "LB-003": "ASSY", "ASSEM-LINE-1": "ASSY", "ASSEM-LINE-2": "ASSY",
    "LB-004": "INSPECT", "INSPECT-CMM": "INSPECT", "MC-007": "INSPECT",
    "LB-005": "WELD", "WELD-A": "WELD", "WELD-B": "WELD",
    "SV-001": "ANOD", "SV-002": "HTRT", "SV-003": "NDT",
    "SV-004": "CHEM", "SV-005": "PAINT",
}

# ── Outside service → operation type (OUTSIDE rows carry their kind in service) ─
SERVICE_TO_TYPE = {
    "ANODIZE-II": "ANOD", "ANODIZE-III": "ANOD", "SVC-ANODIZE": "ANOD",
    "HEAT-TREAT": "HTRT", "SVC-HT-SOLN": "HTRT", "SVC-HT-ANNEAL": "HTRT",
    "NDT-UT": "NDT", "NDT-XRAY": "NDT", "SVC-NDT-FPI": "NDT", "SVC-NDT-XRAY": "NDT",
    "PLATING-EN": "PLATE",
    "PAINT-PRIME": "PAINT", "SVC-PAINT": "PAINT",
    "SVC-CHEM-FILM": "CHEM",
    "SVC-WELD-TIG": "WELD",
}


def op_type_for(resource_id, service_id):
    """Classify one operation row. OUTSIDE rows resolve by service_id; everything
    else resolves by resource_id. Falls back across both so a row is only left
    unmapped when neither id is known."""
    if resource_id == "OUTSIDE":
        return SERVICE_TO_TYPE.get(service_id) or RESOURCE_TO_TYPE.get(resource_id)
    return (RESOURCE_TO_TYPE.get(resource_id)
            or (SERVICE_TO_TYPE.get(service_id) if service_id else None))


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Lookup table ----------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operation_type (
            operation_type_id TEXT    NOT NULL PRIMARY KEY,
            description       TEXT    NOT NULL,
            category          TEXT    NOT NULL DEFAULT 'Other',
            resource_id       TEXT,
            active            INTEGER NOT NULL DEFAULT 1
        )
    """)

    # 2. Seed the taxonomy -----------------------------------------------------
    cur.executemany(
        "INSERT OR IGNORE INTO operation_type "
        "(operation_type_id, description, category, resource_id, active) "
        "VALUES (?,?,?,?,?)",
        OPERATION_TYPES,
    )
    print(f"  operation_type: {len(OPERATION_TYPES)} taxonomy rows ensured")

    # 3. Add the column on operation if missing --------------------------------
    cols = {r[1] for r in cur.execute("PRAGMA table_info(operation)")}
    if "operation_type_id" not in cols:
        cur.execute("ALTER TABLE operation ADD COLUMN operation_type_id TEXT")
        print("  operation.operation_type_id: column added")
    else:
        print("  operation.operation_type_id: column already present")

    # 4. Backfill rows that have no type yet -----------------------------------
    rows = cur.execute(
        "SELECT rowid_pk, resource_id, service_id FROM operation "
        "WHERE operation_type_id IS NULL"
    ).fetchall()

    updates, unmapped = [], []
    for rowid_pk, resource_id, service_id in rows:
        ot = op_type_for(resource_id, service_id)
        if ot:
            updates.append((ot, rowid_pk))
        else:
            unmapped.append((rowid_pk, resource_id, service_id))

    if updates:
        cur.executemany(
            "UPDATE operation SET operation_type_id=? WHERE rowid_pk=?", updates
        )
    print(f"  operation: {len(updates)} rows stamped "
          f"({len(rows)} were unstamped, {len(unmapped)} could not be mapped)")

    if unmapped:
        print("  WARNING — unmapped operation rows (left NULL):")
        for rowid_pk, res, svc in unmapped[:20]:
            print(f"    rowid_pk={rowid_pk} resource_id={res!r} service_id={svc!r}")

    conn.commit()

    # Report the resulting distribution for a quick sanity check.
    print("  resulting operation_type distribution:")
    for ot, n in cur.execute(
        "SELECT operation_type_id, COUNT(*) FROM operation "
        "GROUP BY operation_type_id ORDER BY COUNT(*) DESC"
    ):
        print(f"    {ot or '(NULL)':<10} {n}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
