"""
Migration: Add Purchasing / WIP synthetic tables for the manufacturing digital twin.

Scope (as defined):
  - Raw Materials (RM): purchase_order, po_line, receiving, certification
  - WIP: work_order, operation (routing step), shop_resource, labor_ticket, material_issue
  - AP: invoice_header (payables)

Field naming follows dbo.OPERATION DDL conventions:
  - WORKORDER_TYPE: 'M' = Engineering Master, 'W' = Work Order
  - SEQUENCE_NO: operation sequence (routing step number, multiples of 10)
  - RESOURCE_ID: references shop_resource (work center)
  - SERVICE_ID / VENDOR_ID: outside service fields on operation
  - EST/ACT cost columns: estimated vs actual for LAB, BUR, SER

NOTE: this seeder emits plain multiples-of-10 SEQUENCE_NO, only marks ops 'C'
when the whole WO is done (else random Q/Q/S, unordered), never sets
operation.close_date, and emits older work_order.status labels (Open / Released /
In Process / Complete / Closed). The committed manufacturing.db is finished by these
idempotent migrations, which read the live tables (covering rows from this migration
and from scripts/seed_erp_synthetic.py alike), in this order:
  - migrations/regap_and_seed_requirements.py — renumber operation.sequence_no into
    realistic gapped values (e.g. 20, 80, 220), keep labor_ticket.sequence_no
    aligned, and seed operation-level MATERIAL rows in the `requirement` table.
  - migrations/relabel_work_order_status.py — map work_order.status onto the real
    planner vocabulary (unreleased / firmed / released / closed).
  - migrations/backfill_operation_progress.py — derive realistic, sequence-ordered
    job progress (operation.status Q/S/C + close_date) from each work order's
    status, so progress is measured by status/close_date, not by sequence_no.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_purchasing_wip_tables.py

Safe to re-run: CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE.
"""

import sqlite3, os, random
from datetime import date, timedelta, datetime
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── Aerospace part descriptions ───────────────────────────────────────────────
PARTS = [
    ("PN-10010", "Titanium Hex Bolt AN3-10A, 3/8-24 UNF",            "RM",  2.85),
    ("PN-10020", "Hydraulic Line Fitting MS21902D6, AN-6",            "RM", 14.50),
    ("PN-10030", "Aluminum Alloy Sheet 2024-T3, 0.063\" x 12\" x 24\"","RM", 38.00),
    ("PN-10040", "Inconel 718 Sheet, 0.050\" x 6\" x 12\"",           "RM",210.00),
    ("PN-10050", "Precision Ball Bearing ABEC-7, 6205-2RS",           "RM", 22.40),
    ("PN-10060", "Carbon Fiber Panel 3K Twill, 0.125\" x 12\" x 24\"","RM",185.00),
    ("PN-10070", "Hydraulic Actuator Seal Kit, Parker A2K",           "RM", 67.00),
    ("PN-10080", "Fuel System O-Ring Kit, MIL-P-5510, Viton",        "RM", 31.50),
    ("PN-10090", "Structural Rib Extrusion 7075-T6, 2\" x 1\" x 48\"","RM", 92.00),
    ("PN-10100", "Engine Mount Isolator, Lord J-9613-15",             "RM",155.00),
    ("PN-10110", "Flight Control Rod End, AN490HT10",                 "RM", 44.75),
    ("PN-10120", "Avionics Mounting Tray, .063 Alum 6061-T6",         "RM", 28.00),
    ("PN-10130", "Wing Spar Fitting 7050-T7451, LH",                  "RM",520.00),
    ("PN-10140", "Pressure Bulkhead Panel, Composite/Al Honeycomb",   "RM",890.00),
    ("PN-10150", "NAS1149 Washer, Stainless 300 Series",              "RM",  0.45),
    ("PN-10160", "Titanium Fastener Kit MS21250, 100pc",              "RM", 98.00),
    ("PN-10170", "Hydraulic Reservoir Fitting, Eaton 8-8 FJJX",      "RM", 19.80),
    ("PN-10180", "Landing Gear Bracket 4340 Steel, Heat Treated",     "RM",342.00),
    ("PN-10190", "Composite Fairing Panel, Glass/Epoxy 4-ply",        "RM",265.00),
    ("PN-10200", "Phenolic Insulation Block, MIL-I-24768, 2\" thick", "RM", 55.00),
]

# ── Suppliers ─────────────────────────────────────────────────────────────────
SUPPLIERS = [
    # (supplier_id, name, category, cert_level, payment_terms, lead_days, outside_svc)
    ("S-001", "Precision Aerospace Corp",      "Raw Material",    "AS9100D", "Net 45",  14, False),
    ("S-002", "Advanced Alloy Systems Inc",    "Raw Material",    "AS9100D", "Net 30",  21, False),
    ("S-003", "Apex Machined Parts LLC",       "Sub-Assembly",    "AS9100D", "Net 30",  10, False),
    ("S-004", "Titan Fastener Solutions",      "Raw Material",    "NADCAP",  "Net 45",   7, False),
    ("S-005", "Aerojet Seal Systems",          "MRO",             "AS9100D", "Net 30",  12, False),
    ("S-006", "Pacific Coast Composites",      "Sub-Assembly",    "NADCAP",  "Net 60",  30, False),
    ("S-007", "Summit Bearing Technologies",   "MRO",             "AS9100D", "Net 30",   5, False),
    ("S-008", "Desert Aerospace Coatings",     "Outside Service", "NADCAP",  "Net 30",   3, True),
    ("S-009", "SoCal Heat Treatment Inc",      "Outside Service", "NADCAP",  "Net 15",   2, True),
    ("S-010", "Western NDT Services",          "Outside Service", "NADCAP",  "Net 30",   5, True),
    ("S-011", "Coastal Plating & Finishing",   "Outside Service", "NADCAP",  "Net 30",   4, True),
]

# ── Shop Resources (Work Centers) ─────────────────────────────────────────────
SHOP_RESOURCES = [
    # (resource_id, description, resource_type, run_cost_per_hr, bur_per_hr)
    ("CNC-MILL-1",   "CNC Milling Cell #1, Haas VF-4",         "M",  95.00, 42.00),
    ("CNC-MILL-2",   "CNC Milling Cell #2, Mazak Integrex",    "M", 110.00, 48.00),
    ("WELD-A",       "Welding Cell A, TIG Certified",           "M",  75.00, 30.00),
    ("WELD-B",       "Welding Cell B, MIG/TIG",                 "M",  70.00, 28.00),
    ("INSPECT-CMM",  "CMM Inspection, Zeiss Contura G2",        "M",  65.00, 25.00),
    ("ASSEM-LINE-1", "Assembly Line 1, Integration Bay",        "L",  55.00, 22.00),
    ("ASSEM-LINE-2", "Assembly Line 2, Sub-Assembly",           "L",  50.00, 20.00),
    ("LATHE-1",      "CNC Lathe, Mazak QT-350",                 "M",  85.00, 38.00),
    ("DRILL-PRESS",  "Drill Press / Spotface Station",          "M",  45.00, 18.00),
    ("OUTSIDE",      "Outside Service (External Vendor)",       "S",   0.00,  0.00),
]

# ── Outside Services ──────────────────────────────────────────────────────────
SERVICES = [
    # (service_id, description, default_vendor, base_charge)
    ("ANODIZE-III",  "Anodize Type III Hard Coat, MIL-A-8625",  "S-008",  85.00),
    ("ANODIZE-II",   "Anodize Type II, MIL-A-8625",             "S-008",  55.00),
    ("HEAT-TREAT",   "Stress Relief Heat Treatment, AMS 2759",   "S-009", 120.00),
    ("NDT-UT",       "Ultrasonic NDT Inspection, ASNT Level II", "S-010",  95.00),
    ("NDT-XRAY",     "X-Ray Radiography, MIL-STD-453",          "S-010", 145.00),
    ("PLATING-EN",   "Electroless Nickel Plating, MIL-C-26074", "S-011",  75.00),
    ("PAINT-PRIME",  "Primer + Topcoat, MIL-PRF-85285",         "S-008", 160.00),
]

# ── Operation type sequences (routing templates) ──────────────────────────────
# Each template is a list of (seq, resource_id, service_id, run_hrs_std, setup_hrs, is_outside)
ROUTING_TEMPLATES = {
    "AIRFRAME": [
        (10,  "CNC-MILL-1",   None,          2.5, 0.5, False),
        (20,  "CNC-MILL-2",   None,          1.8, 0.3, False),
        (30,  "OUTSIDE",      "HEAT-TREAT",  0.0, 0.0, True),
        (40,  "INSPECT-CMM",  None,          0.8, 0.2, False),
        (50,  "ASSEM-LINE-1", None,          3.0, 0.5, False),
        (60,  "OUTSIDE",      "ANODIZE-III", 0.0, 0.0, True),
    ],
    "FASTENER": [
        (10,  "LATHE-1",      None,          0.5, 0.1, False),
        (20,  "INSPECT-CMM",  None,          0.3, 0.1, False),
        (30,  "OUTSIDE",      "PLATING-EN",  0.0, 0.0, True),
    ],
    "COMPOSITE": [
        (10,  "ASSEM-LINE-2", None,          4.0, 1.0, False),
        (20,  "OUTSIDE",      "NDT-UT",      0.0, 0.0, True),
        (30,  "INSPECT-CMM",  None,          1.0, 0.2, False),
        (40,  "OUTSIDE",      "PAINT-PRIME", 0.0, 0.0, True),
    ],
    "BRACKET": [
        (10,  "CNC-MILL-1",   None,          1.5, 0.3, False),
        (20,  "WELD-A",       None,          1.0, 0.3, False),
        (30,  "OUTSIDE",      "HEAT-TREAT",  0.0, 0.0, True),
        (40,  "INSPECT-CMM",  None,          0.5, 0.1, False),
    ],
}

WO_TYPES = ["AIRFRAME", "FASTENER", "COMPOSITE", "BRACKET"]

STATUSES_WO    = ["Open", "Released", "In Process", "Complete", "Closed"]
STATUSES_OP    = ["Q", "S", "C"]   # Queued, Started, Complete  (matches ERP STATUS NCHAR)
STATUSES_PO    = ["Open", "Received", "Closed", "Cancelled"]
STATUSES_INV   = ["Open", "Approved", "Paid", "Disputed"]
MATCH_STATUSES = ["Matched", "Price_Variance", "Qty_Variance", "Pending"]
CERT_TYPES     = ["CoC", "FAI", "PPAP", "8130-3", "Material_Test_Report"]
INSP_STATUSES  = ["Passed", "Pending", "Failed"]


def rand_date(start_days_ago=180, end_days_ago=0):
    base = date.today()
    d = base - timedelta(days=random.randint(end_days_ago, start_days_ago))
    return d.isoformat()


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── DDL ──────────────────────────────────────────────────────────────────

    cur.executescript("""
    -- Shop Resources (Work Centers + Outside Service buckets)
    CREATE TABLE IF NOT EXISTS shop_resource (
        resource_id      TEXT PRIMARY KEY,
        description      TEXT NOT NULL,
        resource_type    TEXT NOT NULL CHECK(resource_type IN ('M','L','S')),
        -- M=Machine, L=Labor, S=Outside Service
        run_cost_per_hr  REAL DEFAULT 0.0,
        bur_per_hr_run   REAL DEFAULT 0.0,
        active           INTEGER DEFAULT 1,
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Outside Service definitions
    CREATE TABLE IF NOT EXISTS service (
        service_id      TEXT PRIMARY KEY,
        description     TEXT NOT NULL,
        default_vendor  TEXT,          -- FK to suppliers.supplier_id
        base_charge     REAL DEFAULT 0.0,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Work Orders  (WORKORDER_TYPE: 'M' = Eng Master, 'W' = Work Order)
    CREATE TABLE IF NOT EXISTS work_order (
        wo_id            TEXT PRIMARY KEY,   -- e.g. WO-240001
        workorder_type   TEXT NOT NULL CHECK(workorder_type IN ('M','W')),
        part_id          TEXT NOT NULL,
        part_description TEXT NOT NULL,
        quantity         REAL NOT NULL,
        status           TEXT NOT NULL,
        open_date        DATE,
        close_date       DATE,
        required_date    DATE,
        routing_template TEXT,               -- AIRFRAME / FASTENER / etc.
        -- Accumulated actual costs (posted from operations)
        act_lab_cost     REAL DEFAULT 0.0,
        act_bur_cost     REAL DEFAULT 0.0,
        act_ser_cost     REAL DEFAULT 0.0,
        act_mat_cost     REAL DEFAULT 0.0,
        outside_service  INTEGER DEFAULT 0,  -- 1 if any op routes outside
        site_id          TEXT DEFAULT 'SITE-1',
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Operations / Routing Steps  (mirrors dbo.OPERATION)
    CREATE TABLE IF NOT EXISTS operation (
        rowid_pk          INTEGER PRIMARY KEY AUTOINCREMENT,
        wo_id             TEXT NOT NULL,
        workorder_type    TEXT NOT NULL,
        sequence_no       INTEGER NOT NULL,          -- multiples of 10
        resource_id       TEXT NOT NULL,             -- FK → shop_resource
        service_id        TEXT,                      -- FK → service (outside ops only)
        vendor_id         TEXT,                      -- FK → suppliers (outside ops only)
        run_type          TEXT DEFAULT 'HR',         -- HR=per hour, PC=per piece
        setup_hrs         REAL DEFAULT 0.0,
        run_hrs           REAL DEFAULT 0.0,          -- std run hours
        act_setup_hrs     REAL DEFAULT 0.0,
        act_run_hrs       REAL DEFAULT 0.0,
        -- Estimated costs
        est_atl_lab_cost  REAL DEFAULT 0.0,
        est_atl_bur_cost  REAL DEFAULT 0.0,
        est_atl_ser_cost  REAL DEFAULT 0.0,
        -- Actual costs
        act_atl_lab_cost  REAL DEFAULT 0.0,
        act_atl_bur_cost  REAL DEFAULT 0.0,
        act_atl_ser_cost  REAL DEFAULT 0.0,
        status            TEXT DEFAULT 'Q',          -- Q/S/C
        sched_start_date  DATETIME,
        sched_finish_date DATETIME,
        service_begin_date DATETIME,
        close_date        DATETIME,
        -- Outside service dispatch/receipt
        last_disp_date    DATETIME,
        last_recv_date    DATETIME,
        UNIQUE(wo_id, sequence_no)
    );

    -- Purchase Orders
    CREATE TABLE IF NOT EXISTS purchase_order (
        po_id         TEXT PRIMARY KEY,     -- e.g. PO-240001
        supplier_id   TEXT NOT NULL,        -- FK → suppliers
        po_type       TEXT NOT NULL CHECK(po_type IN ('material','outside_service')),
        po_date       DATE NOT NULL,
        required_date DATE,
        status        TEXT NOT NULL,
        total_cost    REAL DEFAULT 0.0,
        wo_id         TEXT,                 -- set for outside_service POs
        service_id    TEXT,                 -- set for outside_service POs
        buyer_id      TEXT DEFAULT 'BUYER-1',
        site_id       TEXT DEFAULT 'SITE-1',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- PO Lines
    CREATE TABLE IF NOT EXISTS po_line (
        line_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id         TEXT NOT NULL,        -- FK → purchase_order
        part_id       TEXT NOT NULL,
        part_description TEXT NOT NULL,
        quantity      REAL NOT NULL,
        unit_cost     REAL NOT NULL,
        line_total    REAL NOT NULL,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Receiving (goods receipts against POs)
    CREATE TABLE IF NOT EXISTS receiving (
        receipt_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id              TEXT NOT NULL,   -- FK → purchase_order
        supplier_id        TEXT NOT NULL,
        part_id            TEXT NOT NULL,
        quantity_ordered   REAL NOT NULL,
        quantity_received  REAL NOT NULL,
        receipt_date       DATE NOT NULL,
        inspection_status  TEXT NOT NULL DEFAULT 'Pending',
        cert_required      INTEGER DEFAULT 0,  -- 1 = CoC/FAI required
        created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Certifications (CoC, FAI, PPAP, 8130-3)
    CREATE TABLE IF NOT EXISTS certification (
        cert_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id    INTEGER,             -- FK → receiving (nullable for stand-alone certs)
        part_id       TEXT NOT NULL,
        supplier_id   TEXT NOT NULL,
        cert_type     TEXT NOT NULL,       -- CoC / FAI / PPAP / 8130-3 / Material_Test_Report
        issued_date   DATE NOT NULL,
        expiry_date   DATE,
        status        TEXT DEFAULT 'Active' CHECK(status IN ('Active','Expired','Revoked')),
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Invoice Header (AP payables)
    CREATE TABLE IF NOT EXISTS invoice_header (
        invoice_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id                 TEXT NOT NULL,   -- FK → purchase_order
        supplier_id           TEXT NOT NULL,
        invoice_number        TEXT NOT NULL UNIQUE,
        invoice_date          DATE NOT NULL,
        due_date              DATE NOT NULL,
        amount_dollars        REAL NOT NULL,
        status                TEXT NOT NULL DEFAULT 'Open',
        payment_date          DATE,
        three_way_match_status TEXT DEFAULT 'Pending',
        created_at            DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Labor Tickets
    CREATE TABLE IF NOT EXISTS labor_ticket (
        ticket_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        wo_id          TEXT NOT NULL,
        sequence_no    INTEGER NOT NULL,     -- matches operation.sequence_no
        employee_id    TEXT NOT NULL,
        resource_id    TEXT NOT NULL,        -- work center where labor was reported
        clock_in       DATETIME NOT NULL,
        clock_out      DATETIME NOT NULL,
        total_hours    REAL NOT NULL,
        labor_cost     REAL NOT NULL,        -- total_hours × resource run_cost_per_hr
        burden_cost    REAL NOT NULL,        -- total_hours × resource bur_per_hr_run
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Material Issues (RM → WIP)
    CREATE TABLE IF NOT EXISTS material_issue (
        issue_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        wo_id       TEXT NOT NULL,
        part_id     TEXT NOT NULL,
        part_description TEXT NOT NULL,
        quantity    REAL NOT NULL,
        unit_cost   REAL NOT NULL,
        total_cost  REAL NOT NULL,
        issue_date  DATE NOT NULL,
        issued_by   TEXT NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    print("Tables created.")

    # ── Seed shop_resource ────────────────────────────────────────────────────
    for r in SHOP_RESOURCES:
        cur.execute("""
            INSERT OR IGNORE INTO shop_resource
                (resource_id, description, resource_type, run_cost_per_hr, bur_per_hr_run)
            VALUES (?,?,?,?,?)
        """, r)
    print(f"  shop_resource: {len(SHOP_RESOURCES)} rows")

    # ── Seed service ──────────────────────────────────────────────────────────
    for s in SERVICES:
        cur.execute("""
            INSERT OR IGNORE INTO service (service_id, description, default_vendor, base_charge)
            VALUES (?,?,?,?)
        """, s)
    print(f"  service: {len(SERVICES)} rows")

    # ── Seed suppliers (merge into existing suppliers table) ──────────────────
    cur.execute("PRAGMA table_info(suppliers)")
    existing_cols = [r[1] for r in cur.fetchall()]
    # Add missing columns if needed
    for col, defn in [
        ("supplier_id",       "TEXT"),
        ("supplier_name",     "TEXT"),
        ("category",          "TEXT"),
        ("certification_level","TEXT"),
        ("payment_terms",     "TEXT"),
        ("lead_time_days",    "INTEGER"),
        ("outside_service",   "INTEGER DEFAULT 0"),
        ("active",            "INTEGER DEFAULT 1"),
    ]:
        if col not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE suppliers ADD COLUMN {col} {defn}")
            except Exception:
                pass

    for sid, name, cat, cert, terms, lead, os_flag in SUPPLIERS:
        cur.execute("""
            INSERT OR IGNORE INTO suppliers
                (supplier_id, supplier_name, category, certification_level,
                 payment_terms, lead_time_days, outside_service, active)
            VALUES (?,?,?,?,?,?,?,1)
        """, (sid, name, cat, cert, terms, lead, int(os_flag)))
    print(f"  suppliers: {len(SUPPLIERS)} rows")

    # ── Seed work_orders ──────────────────────────────────────────────────────
    wo_rows = []
    employees = [f"EMP-{i:03d}" for i in range(1, 16)]

    for i in range(1, 51):
        wo_id    = f"WO-{240000+i:06d}"
        wo_type  = random.choice(["M","M","W","W","W"])   # 40% master, 60% WO
        part     = random.choice(PARTS)
        template = random.choice(WO_TYPES)
        status   = random.choice(STATUSES_WO)
        open_dt  = rand_date(180, 60)
        close_dt = rand_date(59, 1) if status in ("Complete","Closed") else None
        req_dt   = (date.fromisoformat(open_dt) + timedelta(days=random.randint(14, 60))).isoformat()
        qty      = round(random.uniform(1, 25), 0)
        has_os   = any(op[5] for op in ROUTING_TEMPLATES[template])
        wo_rows.append((wo_id, wo_type, part[0], part[1], qty, status,
                        open_dt, close_dt, req_dt, template, 0.0, 0.0, 0.0, 0.0, int(has_os)))

    for row in wo_rows:
        cur.execute("""
            INSERT OR IGNORE INTO work_order
                (wo_id, workorder_type, part_id, part_description, quantity, status,
                 open_date, close_date, required_date, routing_template,
                 act_lab_cost, act_bur_cost, act_ser_cost, act_mat_cost, outside_service)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, row)
    print(f"  work_order: {len(wo_rows)} rows")

    # ── Seed operations (routing steps) ──────────────────────────────────────
    op_count = 0
    po_outside = []   # collect outside service ops to make POs later

    resource_map = {r[0]: r for r in SHOP_RESOURCES}
    service_map  = {s[0]: s for s in SERVICES}

    for row in wo_rows:
        wo_id, wo_type, part_id, part_desc, qty, status, open_dt = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
        template = row[9]
        ops = ROUTING_TEMPLATES[template]
        wo_status_closed = status in ("Complete", "Closed")
        for seq, res_id, svc_id, run_hrs, setup_hrs, is_outside in ops:
            vendor_id = None
            est_lab = est_bur = est_ser = 0.0
            act_lab = act_bur = act_ser = 0.0
            svc_charge = 0.0

            res = resource_map.get(res_id, ("OUTSIDE","","",'S',0.0,0.0))
            run_cost   = res[3]
            bur_cost   = res[4]

            if is_outside and svc_id:
                svc = service_map.get(svc_id)
                if svc:
                    vendor_id  = svc[2]
                    svc_charge = svc[3] * float(qty)
                    est_ser    = svc_charge
                    act_ser    = round(svc_charge * random.uniform(0.90, 1.15), 2) if wo_status_closed else 0.0
                    po_outside.append((wo_id, seq, svc_id, vendor_id, svc_charge, part_id, open_dt))
            else:
                est_lab = round(run_hrs * run_cost * float(qty), 2)
                est_bur = round(run_hrs * bur_cost * float(qty), 2)
                act_hrs = round(run_hrs * random.uniform(0.85, 1.20), 2) if wo_status_closed else 0.0
                act_lab = round(act_hrs * run_cost * float(qty), 2)
                act_bur = round(act_hrs * bur_cost * float(qty), 2)

            op_status = "C" if wo_status_closed else random.choice(["Q","Q","S"])
            sched_start = (date.fromisoformat(open_dt) + timedelta(days=seq//10)).isoformat()
            sched_finish = (date.fromisoformat(sched_start) + timedelta(days=1 + int(run_hrs))).isoformat()

            cur.execute("""
                INSERT OR IGNORE INTO operation
                    (wo_id, workorder_type, sequence_no, resource_id, service_id, vendor_id,
                     setup_hrs, run_hrs, act_run_hrs,
                     est_atl_lab_cost, est_atl_bur_cost, est_atl_ser_cost,
                     act_atl_lab_cost, act_atl_bur_cost, act_atl_ser_cost,
                     status, sched_start_date, sched_finish_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (wo_id, wo_type, seq, res_id, svc_id, vendor_id,
                  setup_hrs, run_hrs, act_hrs if wo_status_closed else 0.0,
                  est_lab, est_bur, est_ser,
                  act_lab, act_bur, act_ser,
                  op_status, sched_start, sched_finish))
            op_count += 1
    print(f"  operation: {op_count} rows")

    # ── Seed purchase_orders (material) ───────────────────────────────────────
    po_count = 0
    line_count = 0
    po_list = []

    material_suppliers = [s for s in SUPPLIERS if not s[6]]

    for i in range(1, 41):
        po_id    = f"PO-M{240000+i:06d}"
        supplier = random.choice(material_suppliers)
        sid      = supplier[0]
        po_date  = rand_date(180, 30)
        req_dt   = (date.fromisoformat(po_date) + timedelta(days=supplier[5]+3)).isoformat()
        status   = random.choice(STATUSES_PO)
        n_lines  = random.randint(1, 4)
        total    = 0.0
        lines    = []
        for _ in range(n_lines):
            part = random.choice(PARTS)
            qty  = round(random.uniform(2, 50), 0)
            cost = round(part[3] * random.uniform(0.95, 1.05), 2)
            lt   = qty * cost
            total += lt
            lines.append((po_id, part[0], part[1], qty, cost, round(lt,2)))

        cur.execute("""
            INSERT OR IGNORE INTO purchase_order
                (po_id, supplier_id, po_type, po_date, required_date, status, total_cost)
            VALUES (?,?,?,?,?,?,?)
        """, (po_id, sid, "material", po_date, req_dt, status, round(total,2)))
        for ln in lines:
            cur.execute("""
                INSERT OR IGNORE INTO po_line
                    (po_id, part_id, part_description, quantity, unit_cost, line_total)
                VALUES (?,?,?,?,?,?)
            """, ln)
            line_count += 1
        po_count += 1
        po_list.append((po_id, sid, "material", po_date, req_dt, status, total, lines))

    print(f"  purchase_order (material): {po_count} rows, {line_count} lines")

    # ── Seed purchase_orders (outside service from operation data) ────────────
    os_po_count = 0
    for wo_id, seq, svc_id, vendor_id, charge, part_id, open_dt in po_outside:
        po_id   = f"PO-S{wo_id[3:]}-{seq:02d}"
        po_date = (date.fromisoformat(open_dt) + timedelta(days=seq//10)).isoformat()
        req_dt  = (date.fromisoformat(po_date) + timedelta(days=5)).isoformat()
        status  = random.choice(["Open","Received","Closed"])
        svc     = service_map.get(svc_id, ("","","",0.0))
        cur.execute("""
            INSERT OR IGNORE INTO purchase_order
                (po_id, supplier_id, po_type, po_date, required_date, status, total_cost, wo_id, service_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (po_id, vendor_id, "outside_service", po_date, req_dt, status, round(charge,2), wo_id, svc_id))
        # single line for service
        cur.execute("""
            INSERT OR IGNORE INTO po_line
                (po_id, part_id, part_description, quantity, unit_cost, line_total)
            VALUES (?,?,?,?,?,?)
        """, (po_id, svc_id, svc[1] if svc else svc_id, 1.0, round(charge,2), round(charge,2)))
        po_list.append((po_id, vendor_id, "outside_service", po_date, req_dt, status, charge, []))
        os_po_count += 1
    print(f"  purchase_order (outside_service): {os_po_count} rows")

    # ── Seed receiving ────────────────────────────────────────────────────────
    recv_count = 0
    recv_list  = []
    for po_id, sid, po_type, po_date, req_dt, status, total, lines in po_list:
        if status in ("Open", "Cancelled"):
            continue
        recv_date = (date.fromisoformat(po_date) + timedelta(days=random.randint(3,14))).isoformat()
        if po_type == "outside_service":
            qty_ord = 1.0
            qty_rcv = 1.0
            part_id = po_id.replace("PO-S","SVC-")
            insp    = random.choice(["Passed","Passed","Passed","Pending"])
            cert_req= 1
            cur.execute("""
                INSERT OR IGNORE INTO receiving
                    (po_id, supplier_id, part_id, quantity_ordered, quantity_received,
                     receipt_date, inspection_status, cert_required)
                VALUES (?,?,?,?,?,?,?,?)
            """, (po_id, sid, part_id, qty_ord, qty_rcv, recv_date, insp, cert_req))
            recv_list.append((cur.lastrowid, po_id, sid, part_id, recv_date, insp))
        else:
            for _, part_id, part_desc, qty, unit_cost, _ in lines:
                qty_rcv = qty if random.random() > 0.1 else round(qty * random.uniform(0.7,0.99), 0)
                insp    = random.choice(["Passed","Passed","Passed","Pending","Failed"])
                cert_req= 1 if random.random() > 0.4 else 0
                cur.execute("""
                    INSERT OR IGNORE INTO receiving
                        (po_id, supplier_id, part_id, quantity_ordered, quantity_received,
                         receipt_date, inspection_status, cert_required)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (po_id, sid, part_id, qty, qty_rcv, recv_date, insp, cert_req))
                recv_list.append((cur.lastrowid, po_id, sid, part_id, recv_date, insp))
                recv_count += 1
    print(f"  receiving: {recv_count} rows")

    # ── Seed certifications ───────────────────────────────────────────────────
    cert_count = 0
    for recv_id, po_id, sid, part_id, recv_date, insp in recv_list:
        if insp == "Failed":
            continue
        if random.random() < 0.7:
            cert_type  = random.choice(CERT_TYPES)
            issued     = recv_date
            expiry_dt  = (date.fromisoformat(recv_date) + timedelta(days=365)).isoformat()
            cur.execute("""
                INSERT OR IGNORE INTO certification
                    (receipt_id, part_id, supplier_id, cert_type, issued_date, expiry_date, status)
                VALUES (?,?,?,?,?,?,?)
            """, (recv_id, part_id, sid, cert_type, issued, expiry_dt, "Active"))
            cert_count += 1
    print(f"  certification: {cert_count} rows")

    # ── Seed invoice_header ───────────────────────────────────────────────────
    inv_count = 0
    for po_id, sid, po_type, po_date, req_dt, status, total, *_ in po_list:
        if status not in ("Received", "Closed"):
            continue
        inv_no   = f"INV-{fake.bothify('??####').upper()}"
        inv_date = (date.fromisoformat(po_date) + timedelta(days=random.randint(5,20))).isoformat()
        # Payment terms from supplier
        sup      = next((s for s in SUPPLIERS if s[0]==sid), None)
        terms_days = {"Net 15":15,"Net 30":30,"Net 45":45,"Net 60":60}.get(
            sup[4] if sup else "Net 30", 30)
        due_dt   = (date.fromisoformat(inv_date) + timedelta(days=terms_days)).isoformat()
        amt      = round(total * random.uniform(0.98, 1.02), 2)
        inv_status= random.choice(STATUSES_INV)
        pay_dt   = rand_date(30,1) if inv_status == "Paid" else None
        match    = random.choices(
            MATCH_STATUSES, weights=[70,10,10,10])[0]
        cur.execute("""
            INSERT OR IGNORE INTO invoice_header
                (po_id, supplier_id, invoice_number, invoice_date, due_date,
                 amount_dollars, status, payment_date, three_way_match_status)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (po_id, sid, inv_no, inv_date, due_dt, amt, inv_status, pay_dt, match))
        inv_count += 1
    print(f"  invoice_header: {inv_count} rows")

    # ── Seed labor_tickets ────────────────────────────────────────────────────
    lab_count = 0
    for row in wo_rows:
        wo_id, wo_type, part_id, status, open_dt = row[0], row[1], row[2], row[5], row[6]
        if status not in ("In Process","Complete","Closed"):
            continue
        cur.execute("SELECT sequence_no, resource_id, run_hrs FROM operation WHERE wo_id=? AND service_id IS NULL", (wo_id,))
        ops = cur.fetchall()
        for seq, res_id, run_hrs in ops:
            if run_hrs == 0:
                continue
            res    = resource_map.get(res_id)
            if not res:
                continue
            emp_id = random.choice(employees)
            base   = date.fromisoformat(open_dt) + timedelta(days=seq//10)
            cin    = datetime.combine(base, datetime.min.time()).replace(
                       hour=random.randint(6,14), minute=random.choice([0,15,30,45]))
            hours  = round(run_hrs * random.uniform(0.85,1.20), 2)
            cout   = cin + timedelta(hours=hours)
            lab_c  = round(hours * res[3], 2)
            bur_c  = round(hours * res[4], 2)
            cur.execute("""
                INSERT OR IGNORE INTO labor_ticket
                    (wo_id, sequence_no, employee_id, resource_id,
                     clock_in, clock_out, total_hours, labor_cost, burden_cost)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (wo_id, seq, emp_id, res_id,
                  cin.isoformat(), cout.isoformat(), hours, lab_c, bur_c))
            lab_count += 1
    print(f"  labor_ticket: {lab_count} rows")

    # ── Seed material_issues ──────────────────────────────────────────────────
    iss_count = 0
    for row in wo_rows:
        wo_id, wo_type, part_id, part_desc, qty, status, open_dt = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
        if status not in ("In Process","Complete","Closed"):
            continue
        n_issues = random.randint(1, 3)
        for _ in range(n_issues):
            mat  = random.choice(PARTS)
            iss_qty  = round(random.uniform(1, qty), 1)
            unit_c   = round(mat[3] * random.uniform(0.95,1.05), 2)
            iss_date = rand_date(120, 1)
            cur.execute("""
                INSERT OR IGNORE INTO material_issue
                    (wo_id, part_id, part_description, quantity, unit_cost, total_cost, issue_date, issued_by)
                VALUES (?,?,?,?,?,?,?,?)
            """, (wo_id, mat[0], mat[1], iss_qty, unit_c,
                  round(iss_qty*unit_c,2), iss_date,
                  random.choice(employees)))
            iss_count += 1
    print(f"  material_issue: {iss_count} rows")

    conn.commit()
    conn.close()
    print("\nDone. Purchasing / WIP synthetic tables seeded.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
