"""Split receiving into header + line, align payables at line level, and
broaden the purchased commodity mix.

What this does (all deterministic, idempotent, fail-closed):

1. Creates ``receiving_line`` (receipt header stays ``receiving`` — NO renames).
   Backfills exactly one line per existing receiving row (line_no = 1),
   linking each line to its po_line where a (po_id, part_id) match exists.
2. Adds ``payable_line.po_line_id`` and ``payable_line.receipt_line_id`` so
   invoices align at line level (three-way match: PO line <-> receipt line
   <-> payable line). Backfills every matchable row.
3. Adds ``part.commodity_code`` and backfills every part from deterministic
   rules (RAW-METAL, HARDWARE, COMPOSITE, ELECTRICAL, SEAL, BEARING, CASTING,
   MACHINED-DETAIL, ASSEMBLY, OSP-THERMAL, OSP-NDT, OSP-FINISHING, TOOLING,
   SHOP-SUPPLY, PURCHASED-COMPONENT).
4. Adds new purchased commodities: 4 shop-consumable parts, 1 MRO supplier,
   and 5 new purchase orders (3 outside-processing service POs — heat treat,
   anodize, NDT — 1 standards-hardware PO, 1 consumables PO) with lines,
   receipts, receipt lines, invoices, line-level payables, certs and
   inventory receipt transactions. Total POs stays within the 10-20 demo band.
5. Registers receiving_line in schema_nodes / schema_edges for the graph
   exporter, and the new line-level FK edges.

All dates are anchored to the data-derived AS_OF = MAX(work_order.close_date),
never wall-clock. No randomness anywhere.
"""

import os
import sqlite3
import sys
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ---------------------------------------------------------------------------
# fixed demo data (deterministic)
# ---------------------------------------------------------------------------

NEW_SUPPLIER = (
    "S-027", "Industrial Tooling Supply Co", "orders@indtoolsupply.example",
    "555-0127", "4410 Commerce Dr, Wichita, KS", 4.6, "ISO 9001",
    "MRO Supplies", "Net 30", 5, 0, 1,
)

# (part_id, description, part_class, uom, unit_cost, lead_days, mat_spec)
NEW_PARTS = [
    ("C-20001", "Carbide End Mill 0.500 4FL TiAlN",          "BUY", "EA",  42.50,  5, "ISO 1832"),
    ("C-20002", "Coolant Concentrate Semi-Synthetic 55 Gal", "BUY", "DR", 780.00,  7, "MIL-PRF-680"),
    ("C-20003", "Abrasive Disc 120 Grit 5 in (50 Pack)",     "BUY", "PK",  28.40,  5, "ANSI B74.18"),
    ("C-20004", "CMM Stylus Ruby 4mm M3",                    "BUY", "EA",  96.00, 10, "ISO 10360"),
]

# service_id -> (description, default_vendor, base_charge)
# Referenced by the outside-service POs below; inserted idempotently so a
# fresh-clone bootstrap (whose seeder ships a different service catalog)
# satisfies the FK-style orphan check.
NEW_SERVICES = {
    "HEAT-TREAT": ("Stress Relief Heat Treatment, AMS 2759", "S-009", 120.0),
    "ANODIZE-II": ("Anodize Type II, MIL-A-8625", "S-008", 55.0),
    "NDT-UT": ("Ultrasonic NDT Inspection, ASNT Level II", "S-010", 95.0),
}

# po_id -> (supplier, po_type, service_id, status, po_offset_days, req_offset_days)
NEW_POS = {
    "PO-SVC-001": ("S-009", "outside_service", "HEAT-TREAT", "Closed",  -75, -45),
    "PO-SVC-002": ("S-015", "outside_service", "ANODIZE-II", "Open",    -10,  20),
    "PO-SVC-003": ("S-010", "outside_service", "NDT-UT",     "Partial", -30,  -2),
    "PO-STD-001": ("S-013", "material",        None,         "Closed",  -60, -30),
    "PO-CON-001": ("S-027", "material",        None,         "Open",     -5,   9),
}

# po_id -> [(part_id, qty)]  (unit cost always read from part.unit_cost)
NEW_PO_LINES = {
    "PO-SVC-001": [("P-10028", 24)],
    "PO-SVC-002": [("P-10027", 36)],
    "PO-SVC-003": [("P-10029", 18)],
    "PO-STD-001": [("PN-10010", 200), ("P-10019", 500), ("P-10021", 250), ("P-10022", 200)],
    "PO-CON-001": [("C-20001", 10), ("C-20002", 2), ("C-20003", 20), ("C-20004", 2)],
}

# po_id -> (receipt_offset_days, [(part_id, qty_received, inspection, cert_required)])
NEW_RECEIPTS = {
    "PO-SVC-001": (-50, [("P-10028", 24, "Passed", 1)]),
    "PO-SVC-003": (-12, [("P-10029", 10, "Passed", 1)]),
    "PO-STD-001": (-40, [("PN-10010", 200, "Passed", 1), ("P-10019", 500, "Passed", 0),
                         ("P-10021", 250, "Passed", 0), ("P-10022", 200, "Passed", 0)]),
}

# po_id -> (status, match_status, inv_offset_from_receipt, paid: bool)
NEW_INVOICES = {
    "PO-SVC-001": ("Paid", "Matched", 5, True),
    "PO-SVC-003": ("Open", "Pending", 4, False),
    "PO-STD-001": ("Open", "Matched", 5, False),
}

# part_id -> cert_type for new cert-required receipts
CERT_TYPE_BY_PART = {
    "P-10028": "Material_Test_Report",
    "P-10029": "CoC",
    "PN-10010": "CoC",
}

# ordered, deterministic commodity rules: (test, code)
def commodity_code_for(part_id, part_class, desc):
    d = desc.lower()
    if part_class == "OUTSIDE_SERVICE":
        if "heat treat" in d:
            return "OSP-THERMAL"
        if "ndt" in d or "penetrant" in d or "x-ray" in d or "radiograph" in d:
            return "OSP-NDT"
        return "OSP-FINISHING"
    if part_id.startswith("C-2"):
        return "TOOLING" if ("end mill" in d or "stylus" in d) else "SHOP-SUPPLY"
    if part_class == "HARDWARE":
        return "HARDWARE"
    if part_class == "RAW":
        return "RAW-METAL"
    if part_class == "BUY":
        if "composite" in d or "carbon fiber" in d:
            return "COMPOSITE"
        if "harness" in d or "avionics" in d or "electrical" in d:
            return "ELECTRICAL"
        if "bearing" in d:
            return "BEARING"
        if "o-ring" in d or "seal" in d:
            return "SEAL"
        if "casting" in d:
            return "CASTING"
        if any(k in d for k in ("fastener", "bolt", "washer", "nut", "fitting")):
            return "HARDWARE"
        return "PURCHASED-COMPONENT"
    # MAKE
    if "assembly" in d or "assy" in d:
        return "ASSEMBLY"
    return "MACHINED-DETAIL"


def fmt(d):
    return d.isoformat() if d else None


def column_exists(cur, table, column):
    return column in {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}


def get_as_of(cur):
    row = cur.execute(
        "SELECT MAX(close_date) FROM work_order WHERE close_date IS NOT NULL"
    ).fetchone()
    if not row or not row[0]:
        raise SystemExit("FAIL-CLOSED: cannot derive AS_OF from work_order.close_date")
    return date.fromisoformat(row[0][:10])


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def create_receiving_line(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS receiving_line (
            receipt_line_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id        INTEGER NOT NULL REFERENCES receiving(receipt_id),
            line_no           INTEGER NOT NULL,
            po_line_id        INTEGER REFERENCES po_line(line_id),
            part_id           TEXT NOT NULL REFERENCES part(part_id),
            quantity_ordered  REAL NOT NULL,
            quantity_received REAL NOT NULL,
            inspection_status TEXT NOT NULL DEFAULT 'Pending',
            cert_required     INTEGER DEFAULT 0,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (receipt_id, line_no)
        )
    """)


def alter_payable_line(cur):
    if not column_exists(cur, "payable_line", "po_line_id"):
        cur.execute("ALTER TABLE payable_line ADD COLUMN po_line_id INTEGER "
                    "REFERENCES po_line(line_id)")
    if not column_exists(cur, "payable_line", "receipt_line_id"):
        cur.execute("ALTER TABLE payable_line ADD COLUMN receipt_line_id INTEGER "
                    "REFERENCES receiving_line(receipt_line_id)")


def alter_part(cur):
    if not column_exists(cur, "part", "commodity_code"):
        cur.execute("ALTER TABLE part ADD COLUMN commodity_code TEXT")


# ---------------------------------------------------------------------------
# new commodity data
# ---------------------------------------------------------------------------

def insert_supplier_and_parts(cur):
    cur.execute(
        "INSERT OR IGNORE INTO suppliers (supplier_id, supplier_name, contact_email, "
        "phone, address, performance_rating, certification_level, category, "
        "payment_terms, lead_time_days, outside_service, active) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (NEW_SUPPLIER[0], NEW_SUPPLIER[1], NEW_SUPPLIER[2], NEW_SUPPLIER[3],
         NEW_SUPPLIER[4], NEW_SUPPLIER[5], NEW_SUPPLIER[6], NEW_SUPPLIER[7],
         NEW_SUPPLIER[8], NEW_SUPPLIER[9], NEW_SUPPLIER[10], NEW_SUPPLIER[11]),
    )
    for part_id, desc, pclass, uom, cost, lead, spec in NEW_PARTS:
        cur.execute(
            "INSERT OR IGNORE INTO part (part_id, part_description, part_class, "
            "unit_of_measure, unit_cost, lead_time_days, material_spec, active) "
            "VALUES (?,?,?,?,?,?,?,1)",
            (part_id, desc, pclass, uom, cost, lead, spec),
        )


def backfill_commodity_codes(cur):
    rows = cur.execute(
        "SELECT part_id, part_class, part_description FROM part "
        "WHERE commodity_code IS NULL"
    ).fetchall()
    for part_id, pclass, desc in rows:
        cur.execute(
            "UPDATE part SET commodity_code=? WHERE part_id=?",
            (commodity_code_for(part_id, pclass, desc), part_id),
        )
    return len(rows)


def insert_new_pos(cur, as_of):
    open_wos = [r[0] for r in cur.execute(
        "SELECT wo_id FROM work_order WHERE status NOT IN ('Closed','Cancelled') "
        "ORDER BY wo_id"
    ).fetchall()]
    svc_ids = [p for p in NEW_POS if NEW_POS[p][1] == "outside_service"]
    wo_for = {p: (open_wos[i % len(open_wos)] if open_wos else None)
              for i, p in enumerate(sorted(svc_ids))}

    unit_cost = {r[0]: r[1] for r in cur.execute(
        "SELECT part_id, unit_cost FROM part").fetchall()}
    desc_of = {r[0]: r[1] for r in cur.execute(
        "SELECT part_id, part_description FROM part").fetchall()}

    for svc_id, (desc, vendor, charge) in NEW_SERVICES.items():
        cur.execute(
            "INSERT OR IGNORE INTO service (service_id, description, "
            "default_vendor, base_charge) VALUES (?,?,?,?)",
            (svc_id, desc, vendor, charge),
        )

    for po_id, (sup, po_type, svc, status, po_off, req_off) in NEW_POS.items():
        if cur.execute("SELECT 1 FROM purchase_order WHERE po_id=?", (po_id,)).fetchone():
            continue
        lines = NEW_PO_LINES[po_id]
        total = round(sum(qty * unit_cost[p] for p, qty in lines), 2)
        cur.execute(
            "INSERT INTO purchase_order (po_id, supplier_id, po_type, po_date, "
            "required_date, status, total_cost, wo_id, service_id, buyer_id, site_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (po_id, sup, po_type, fmt(as_of + timedelta(days=po_off)),
             fmt(as_of + timedelta(days=req_off)), status, total,
             wo_for.get(po_id), svc, "BUYER-2", "SITE-1"),
        )
        for part_id, qty in lines:
            cur.execute(
                "INSERT INTO po_line (po_id, part_id, part_description, quantity, "
                "unit_cost, line_total) VALUES (?,?,?,?,?,?)",
                (po_id, part_id, desc_of[part_id], qty, unit_cost[part_id],
                 round(qty * unit_cost[part_id], 2)),
            )


def insert_new_receipts(cur, as_of):
    for po_id, (off, lines) in NEW_RECEIPTS.items():
        sup = cur.execute(
            "SELECT supplier_id FROM purchase_order WHERE po_id=?", (po_id,)
        ).fetchone()[0]
        recv_d = fmt(as_of + timedelta(days=off))
        for part_id, qty_recv, insp, cert_req in lines:
            if cur.execute(
                "SELECT 1 FROM receiving WHERE po_id=? AND part_id=?", (po_id, part_id)
            ).fetchone():
                continue
            qty_ord = cur.execute(
                "SELECT quantity FROM po_line WHERE po_id=? AND part_id=? "
                "ORDER BY line_id LIMIT 1", (po_id, part_id)
            ).fetchone()[0]
            cur.execute(
                "INSERT INTO receiving (po_id, supplier_id, part_id, quantity_ordered, "
                "quantity_received, receipt_date, inspection_status, cert_required) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (po_id, sup, part_id, qty_ord, qty_recv, recv_d, insp, cert_req),
            )


def backfill_receiving_lines(cur):
    """One receiving_line per receiving header row that has none (line_no=1)."""
    cur.execute("""
        INSERT INTO receiving_line
            (receipt_id, line_no, po_line_id, part_id, quantity_ordered,
             quantity_received, inspection_status, cert_required)
        SELECT r.receipt_id, 1,
               (SELECT MIN(pl.line_id) FROM po_line pl
                 WHERE pl.po_id = r.po_id AND pl.part_id = r.part_id),
               r.part_id, r.quantity_ordered, r.quantity_received,
               r.inspection_status, r.cert_required
        FROM receiving r
        WHERE NOT EXISTS (SELECT 1 FROM receiving_line rl
                          WHERE rl.receipt_id = r.receipt_id)
    """)
    return cur.rowcount


def insert_new_invoices(cur, as_of):
    max_num = cur.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(invoice_number, 5) AS INTEGER)), 0) "
        "FROM payables WHERE invoice_number LIKE 'INV-%'"
    ).fetchone()[0]

    for po_id in sorted(NEW_INVOICES):
        status, match, inv_off, paid = NEW_INVOICES[po_id]
        if cur.execute(
            "SELECT 1 FROM payables WHERE po_id=?", (po_id,)
        ).fetchone():
            continue
        recv_off, _lines = NEW_RECEIPTS[po_id]
        sup = cur.execute(
            "SELECT supplier_id FROM purchase_order WHERE po_id=?", (po_id,)
        ).fetchone()[0]
        recv_d = as_of + timedelta(days=recv_off)
        inv_d = recv_d + timedelta(days=inv_off)
        due_d = inv_d + timedelta(days=30)
        pay_d = fmt(due_d - timedelta(days=10)) if paid else None

        # line-level amounts from receipt lines x po_line unit cost
        recv_lines = cur.execute("""
            SELECT rl.receipt_line_id, rl.po_line_id, rl.part_id,
                   rl.quantity_received, pl.unit_cost
            FROM receiving_line rl
            JOIN receiving r ON r.receipt_id = rl.receipt_id
            JOIN po_line pl ON pl.line_id = rl.po_line_id
            WHERE r.po_id = ?
            ORDER BY rl.receipt_line_id
        """, (po_id,)).fetchall()
        if not recv_lines:
            raise SystemExit(f"FAIL-CLOSED: no receipt lines to invoice for {po_id}")
        amount = round(sum(q * c for _, _, _, q, c in recv_lines), 2)

        max_num += 1
        cur.execute(
            "INSERT INTO payables (po_id, supplier_id, invoice_number, "
            "invoice_date, due_date, amount_dollars, status, payment_date, "
            "three_way_match_status) VALUES (?,?,?,?,?,?,?,?,?)",
            (po_id, sup, f"INV-{max_num:06d}", fmt(inv_d), fmt(due_d),
             amount, status, pay_d, match),
        )
        invoice_id = cur.lastrowid
        for line_no, (rl_id, pl_id, part_id, qty, cost) in enumerate(recv_lines, 1):
            cur.execute(
                "INSERT INTO payable_line (invoice_id, line_no, po_id, part_id, qty, "
                "amount, po_line_id, receipt_line_id) VALUES (?,?,?,?,?,?,?,?)",
                (invoice_id, line_no, po_id, part_id, qty,
                 round(qty * cost, 2), pl_id, rl_id),
            )


def backfill_payable_line_links(cur):
    cur.execute("""
        UPDATE payable_line SET po_line_id = (
            SELECT MIN(pl.line_id) FROM po_line pl
            WHERE pl.po_id = payable_line.po_id
              AND pl.part_id = payable_line.part_id)
        WHERE po_line_id IS NULL AND po_id IS NOT NULL AND part_id IS NOT NULL
    """)
    cur.execute("""
        UPDATE payable_line SET receipt_line_id = (
            SELECT MIN(rl.receipt_line_id)
            FROM receiving_line rl JOIN receiving r ON r.receipt_id = rl.receipt_id
            WHERE r.po_id = payable_line.po_id
              AND rl.part_id = payable_line.part_id)
        WHERE receipt_line_id IS NULL AND po_id IS NOT NULL AND part_id IS NOT NULL
    """)


def insert_new_certs(cur):
    rows = cur.execute("""
        SELECT r.receipt_id, r.part_id, r.supplier_id, r.receipt_date
        FROM receiving r
        WHERE r.cert_required = 1
          AND NOT EXISTS (SELECT 1 FROM certification c
                          WHERE c.receipt_id = r.receipt_id)
        ORDER BY r.receipt_id
    """).fetchall()
    for receipt_id, part_id, sup, recv_date in rows:
        cert_t = CERT_TYPE_BY_PART.get(part_id, "CoC")
        recv_d = date.fromisoformat(recv_date[:10])
        expiry = fmt(recv_d + timedelta(days=365)) if cert_t == "CoC" else None
        cur.execute(
            "INSERT INTO certification (receipt_id, part_id, supplier_id, cert_type, "
            "issued_date, expiry_date, status) VALUES (?,?,?,?,?,?,'Active')",
            (receipt_id, part_id, sup, cert_t, fmt(recv_d), expiry),
        )
    return len(rows)


def insert_inventory_receipts(cur):
    """Stock receipt transactions for the standards-hardware PO."""
    rows = cur.execute("""
        SELECT r.part_id, r.quantity_received, r.receipt_date
        FROM receiving r
        WHERE r.po_id = 'PO-STD-001'
          AND NOT EXISTS (SELECT 1 FROM inventory_transaction t
                          WHERE t.po_id = 'PO-STD-001' AND t.part_id = r.part_id
                            AND t.class = 'R')
        ORDER BY r.receipt_id
    """).fetchall()
    for part_id, qty, recv_date in rows:
        cur.execute(
            "INSERT INTO inventory_transaction (class, type, part_id, wo_id, po_id, "
            "site_id, quantity, trans_date) VALUES ('R','I',?,NULL,'PO-STD-001',"
            "'SITE-1',?,?)",
            (part_id, qty, recv_date),
        )
    # Grounding invariant (enforced by backfill_pn_parts_master_and_planner):
    # any PN-* part with ledger rows must have on_hand_qty == ledger net
    # (floored at 0). The receipts above may be a PN part's FIRST ledger rows,
    # so resync on_hand from the ledger for every PN-* part on this PO.
    # Idempotent: always sets on_hand to the current ledger net.
    cur.execute("""
        UPDATE part SET on_hand_qty = (
            SELECT MAX(0, ROUND(SUM(CASE WHEN t.type='I' THEN t.quantity
                                         ELSE -t.quantity END), 1))
            FROM inventory_transaction t WHERE t.part_id = part.part_id
        )
        WHERE part_id LIKE 'PN-%'
          AND part_id IN (SELECT part_id FROM receiving WHERE po_id = 'PO-STD-001')
          AND EXISTS (SELECT 1 FROM inventory_transaction t
                      WHERE t.part_id = part.part_id)
    """)
    return len(rows)


# ---------------------------------------------------------------------------
# semantic-layer registration
# ---------------------------------------------------------------------------

def register_in_semantic_layer(cur):
    cur.execute(
        "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
        "VALUES ('receiving_line', 'Table', "
        "'Line items on a goods receipt — one row per part received, linked to the "
        "PO line for line-level three-way match')"
    )
    # INSERT OR IGNORE below only dedupes if the logical unique index exists
    # (a fresh-clone DB may predate it). Dedupe first, then ensure the index.
    cur.execute("""
        DELETE FROM schema_edges WHERE edge_id NOT IN (
            SELECT MIN(edge_id) FROM schema_edges
            GROUP BY from_table, to_table, join_column
        )
    """)
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_schema_edges_logical "
        "ON schema_edges(from_table, to_table, join_column)"
    )
    new_edges = [
        ("receiving_line", "receiving", "FOREIGN_KEY", "receipt_id",
         "Receipt line belongs to a receiving header"),
        ("receiving_line", "po_line", "FOREIGN_KEY", "po_line_id",
         "Receipt line closes against a purchase-order line"),
        ("receiving_line", "part", "FOREIGN_KEY", "part_id",
         "Receipt line records the received part"),
        ("payable_line", "po_line", "FOREIGN_KEY", "po_line_id",
         "Payable line matches a purchase-order line"),
        ("payable_line", "receiving_line", "FOREIGN_KEY", "receipt_line_id",
         "Payable line matches a receipt line (three-way match)"),
    ]
    for from_t, to_t, rel, col, desc in new_edges:
        nxt = cur.execute(
            "SELECT COALESCE(MAX(edge_id), 0) + 1 FROM schema_edges"
        ).fetchone()[0]
        cur.execute(
            "INSERT OR IGNORE INTO schema_edges (edge_id, from_table, to_table, "
            "relationship_type, join_column, weight, join_column_description) "
            "VALUES (?,?,?,?,?,1,?)",
            (nxt, from_t, to_t, rel, col, desc),
        )


# ---------------------------------------------------------------------------
# fail-closed validation
# ---------------------------------------------------------------------------

def validate(cur, as_of):
    failures = []

    # PO band top is 25 (not 20): a fresh-clone bootstrap seeds 15 POs, the
    # MRP backfill may add a deterministic top-up PO, and this migration adds 5.
    n_po = cur.execute("SELECT COUNT(*) FROM purchase_order").fetchone()[0]
    if not (10 <= n_po <= 25):
        failures.append(f"purchase_order count {n_po} outside demo band [10, 25]")
    for po_id in NEW_POS:
        if not cur.execute("SELECT 1 FROM purchase_order WHERE po_id=?", (po_id,)).fetchone():
            failures.append(f"missing expected PO {po_id}")

    # header/line coverage: every receiving row has lines; qty sums match header
    n = cur.execute("""
        SELECT COUNT(*) FROM receiving r
        WHERE NOT EXISTS (SELECT 1 FROM receiving_line rl
                          WHERE rl.receipt_id = r.receipt_id)
    """).fetchone()[0]
    if n:
        failures.append(f"{n} receiving headers without receiving_line rows")
    n = cur.execute("""
        SELECT COUNT(*) FROM receiving r
        JOIN (SELECT receipt_id, SUM(quantity_received) qs
              FROM receiving_line GROUP BY receipt_id) x
          ON x.receipt_id = r.receipt_id
        WHERE ABS(x.qs - r.quantity_received) > 0.001
    """).fetchone()[0]
    if n:
        failures.append(f"{n} receipts where line qty sum != header qty")

    orphan_checks = [
        ("receiving_line", "receipt_id NOT IN (SELECT receipt_id FROM receiving)"),
        ("receiving_line", "po_line_id IS NOT NULL AND po_line_id NOT IN "
                           "(SELECT line_id FROM po_line)"),
        ("receiving_line", "part_id NOT IN (SELECT part_id FROM part)"),
        ("payable_line", "po_line_id IS NOT NULL AND po_line_id NOT IN "
                         "(SELECT line_id FROM po_line)"),
        ("payable_line", "receipt_line_id IS NOT NULL AND receipt_line_id NOT IN "
                         "(SELECT receipt_line_id FROM receiving_line)"),
        ("payable_line", "invoice_id NOT IN (SELECT invoice_id FROM payables)"),
        ("certification", "receipt_id IS NOT NULL AND receipt_id NOT IN "
                          "(SELECT receipt_id FROM receiving)"),
        ("po_line", "po_id NOT IN (SELECT po_id FROM purchase_order)"),
        ("receiving", "po_id NOT IN (SELECT po_id FROM purchase_order)"),
        ("payables", "po_id NOT IN (SELECT po_id FROM purchase_order)"),
        ("inventory_transaction", "po_id IS NOT NULL AND po_id NOT IN "
                                  "(SELECT po_id FROM purchase_order)"),
        ("purchase_order", "service_id IS NOT NULL AND service_id NOT IN "
                           "(SELECT service_id FROM service)"),
        ("purchase_order", "supplier_id NOT IN (SELECT supplier_id FROM suppliers)"),
        ("purchase_order", "wo_id IS NOT NULL AND wo_id NOT IN "
                           "(SELECT wo_id FROM work_order)"),
    ]
    for table, cond in orphan_checks:
        n = cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {cond}").fetchone()[0]
        if n:
            failures.append(f"{n} orphan rows in {table} ({cond[:60]}...)")

    # matchable ⇒ matched (line-level three-way alignment)
    n = cur.execute("""
        SELECT COUNT(*) FROM receiving_line rl
        JOIN receiving r ON r.receipt_id = rl.receipt_id
        WHERE rl.po_line_id IS NULL
          AND EXISTS (SELECT 1 FROM po_line pl
                      WHERE pl.po_id = r.po_id AND pl.part_id = rl.part_id)
    """).fetchone()[0]
    if n:
        failures.append(f"{n} receiving_line rows unmatched despite matching po_line")
    n = cur.execute("""
        SELECT COUNT(*) FROM payable_line y
        WHERE y.po_line_id IS NULL AND y.po_id IS NOT NULL AND y.part_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM po_line pl
                      WHERE pl.po_id = y.po_id AND pl.part_id = y.part_id)
    """).fetchone()[0]
    if n:
        failures.append(f"{n} payable_line rows unmatched despite matching po_line")

    # totals & commodity coverage
    n = cur.execute("""
        SELECT COUNT(*) FROM purchase_order po
        WHERE po.po_id IN ({}) AND ABS(po.total_cost - (
            SELECT COALESCE(SUM(line_total), 0) FROM po_line
            WHERE po_line.po_id = po.po_id)) > 0.01
    """.format(",".join(f"'{p}'" for p in NEW_POS))).fetchone()[0]
    if n:
        failures.append(f"{n} new POs where total_cost != SUM(po_line.line_total)")
    n = cur.execute(
        "SELECT COUNT(*) FROM part WHERE commodity_code IS NULL OR commodity_code=''"
    ).fetchone()[0]
    if n:
        failures.append(f"{n} parts without commodity_code")

    # cert coverage on new receipts
    n = cur.execute("""
        SELECT COUNT(*) FROM receiving r
        WHERE r.cert_required = 1
          AND NOT EXISTS (SELECT 1 FROM certification c
                          WHERE c.receipt_id = r.receipt_id)
    """).fetchone()[0]
    if n:
        failures.append(f"{n} cert-required receipts without certification")

    # AS_OF anchor unchanged (we never touch work orders)
    if get_as_of(cur) != as_of:
        failures.append("AS_OF anchor drifted — work_order data was modified")

    # semantic registration present
    if not cur.execute(
        "SELECT 1 FROM schema_nodes WHERE table_name='receiving_line'"
    ).fetchone():
        failures.append("receiving_line missing from schema_nodes")
    n = cur.execute(
        "SELECT COUNT(*) FROM schema_edges WHERE from_table='receiving_line' "
        "OR (from_table='payable_line' AND join_column IN "
        "('po_line_id','receipt_line_id'))"
    ).fetchone()[0]
    if n != 5:
        failures.append(f"expected 5 new schema_edges rows, found {n}")

    if failures:
        print("FAIL-CLOSED — validation failures:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


def heal_orphan_receiving_lines(cur):
    """Self-heal receiving_line rows orphaned by earlier runs.

    Older DBs can carry receiving_line rows whose parents were later removed by
    prune_erp_to_demo_scale (which historically did not cascade receiving_line).
    Deleting them here is safe and idempotent: backfill_receiving_lines
    regenerates lines for every surviving receiving header, and payable_line
    receipt refs are re-pointed by backfill_payable_line_links.
    """
    counts = {}
    for label, cond in (
        ("missing receiving header", "receipt_id NOT IN (SELECT receipt_id FROM receiving)"),
        ("missing po_line", "po_line_id IS NOT NULL AND po_line_id NOT IN "
                            "(SELECT line_id FROM po_line)"),
        ("missing part", "part_id NOT IN (SELECT part_id FROM part)"),
    ):
        cur.execute(f"DELETE FROM receiving_line WHERE {cond}")
        if cur.rowcount:
            counts[label] = cur.rowcount
    # payable_line rows may now point at deleted receipt lines — unlink so the
    # re-link backfill can re-point them against the regenerated lines.
    cur.execute(
        "UPDATE payable_line SET receipt_line_id = NULL "
        "WHERE receipt_line_id IS NOT NULL AND receipt_line_id NOT IN "
        "(SELECT receipt_line_id FROM receiving_line)"
    )
    if cur.rowcount:
        counts["payable_line receipt refs unlinked"] = cur.rowcount
    if counts:
        detail = ", ".join(f"{v} ({k})" for k, v in counts.items())
        print(f"self-heal: removed orphaned receiving_line rows — {detail}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        as_of = get_as_of(cur)
        print(f"AS_OF = {as_of}")

        create_receiving_line(cur)
        alter_payable_line(cur)
        alter_part(cur)
        heal_orphan_receiving_lines(cur)

        insert_supplier_and_parts(cur)
        n_comm = backfill_commodity_codes(cur)
        insert_new_pos(cur, as_of)
        insert_new_receipts(cur, as_of)
        n_lines = backfill_receiving_lines(cur)
        insert_new_invoices(cur, as_of)
        backfill_payable_line_links(cur)
        n_certs = insert_new_certs(cur)
        n_txn = insert_inventory_receipts(cur)
        register_in_semantic_layer(cur)

        validate(cur, as_of)
        conn.commit()

        n_po = cur.execute("SELECT COUNT(*) FROM purchase_order").fetchone()[0]
        n_rl = cur.execute("SELECT COUNT(*) FROM receiving_line").fetchone()[0]
        n_pl = cur.execute(
            "SELECT COUNT(*) FROM payable_line WHERE po_line_id IS NOT NULL"
        ).fetchone()[0]
        print(f"commodity codes backfilled: {n_comm}")
        print(f"receiving_line rows created this run: {n_lines} (total {n_rl})")
        print(f"payable lines linked to PO lines: {n_pl}")
        print(f"new certifications: {n_certs}; new inventory receipts: {n_txn}")
        print(f"purchase orders: {n_po} (demo band 10-25)")
        print("All fail-closed checks passed. Done.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
