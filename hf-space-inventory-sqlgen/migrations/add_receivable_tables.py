"""Add the physical AR side of the ledger: receivable + receivable_line.

Mirrors the proven payables / payable_line design with the arrows reversed
(customer_order instead of purchase_order).  Today the Receivables
perspective reads only customer_order.status — there is no invoice-level
grain, so aging, open-AR, and dollars-billed questions have no physical
home.  Grain contract (docs/pods/2026-07-14_receivables-invoice-grain.md):

    one row in receivable       = one AR invoice
    one row in receivable_line  = one invoice line, carrying provenance
                                  back to the commercial commitment
                                  (order_line_id).  Physical-event
                                  provenance (shipment_line_id) is a
                                  nullable placeholder until packslip
                                  tables exist — deliberately NOT a
                                  declared FK (the target table does not
                                  exist yet).

What this migration does (deterministic, idempotent, fail-closed):

1. DDL — creates receivable / receivable_line with declared FKs so the
   metadata exporter (replit_integrations/export_graph_metadata.py) mints
   the structural `references` edges automatically from
   PRAGMA foreign_key_list.
2. REGISTRY — registers both tables in schema_nodes (Schema Browser /
   exporter table enumeration) and adds the join-graph rows to
   schema_edges, mirroring the payables precedent:
       receivable      -> customer_order      (order_id)
       receivable_line -> receivable          (invoice_id)
       receivable_line -> customer_order_line (order_line_id)
3. BACKFILL — invoices the existing order book 1:1 (one invoice per
   billable order; the invoice bills the whole order):
       - Closed orders  -> status Paid, invoice_date = completed_date,
         due_date = invoice_date + 30, payment_date = due_date - 5.
       - Shipped orders -> status Open (unpaid AR), same dating,
         payment_date NULL — EXCEPT the single highest-value Shipped
         order, which becomes Disputed (engineered aging-exception
         population, picked deterministically by billed value then
         order_id).
       - Open / Cancelled orders -> no invoice, by design.
   Lines: one receivable_line per customer_order_line
   (qty = order_qty, amount = ROUND(order_qty * unit_price, 2));
   header amount_dollars = SUM(line amounts) exactly.
   All dates derive from completed_date (data-derived anchor) — never
   wall-clock.  invoice_number = 'AR-' || order_id (unique, 1:1).
4. FAIL-CLOSED VERIFY — re-checks every invariant at the end and exits
   non-zero on any drift:
       - invoice_id / invoice_number unique;
       - every Closed/Shipped order has exactly one invoice; Open and
         Cancelled orders have none;
       - header amount == SUM(line amounts) per invoice (1e-6);
       - every line resolves to a real customer_order_line of the SAME
         order (provenance integrity);
       - status vocabulary respected; Paid => payment_date set,
         Open/Disputed => payment_date NULL;
       - shipment_line_id is NULL everywhere (placeholder contract).

Out of scope, on purpose:
  - No packslip / shipment tables (separate future work).
  - No governed views, palette entries, or intent wiring.
  - No customer_order writes of any kind.

Run once (safe to re-run):
    cd hf-space-inventory-sqlgen
    python migrations/add_receivable_tables.py
"""

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

DDL = """
-- AR invoice header (mirrors payables; arrows point at the demand side)
CREATE TABLE IF NOT EXISTS receivable (
    invoice_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id       TEXT NOT NULL,                 -- FK -> customer_order
    customer_name  TEXT NOT NULL,                 -- denormalized from the order header
    invoice_number TEXT NOT NULL UNIQUE,
    invoice_date   DATE NOT NULL,
    due_date       DATE NOT NULL,
    amount_dollars REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Open'
                   CHECK(status IN ('Open','Paid','Disputed','Void')),
    payment_date   DATE,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES customer_order(order_id)
);

-- AR invoice line (mirrors payable_line; order_line_id = commercial
-- provenance, shipment_line_id = physical provenance placeholder)
CREATE TABLE IF NOT EXISTS receivable_line (
    receivable_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id         INTEGER NOT NULL,
    line_no            INTEGER NOT NULL,
    order_id           TEXT,
    part_id            TEXT,
    qty                REAL,
    amount             REAL NOT NULL,
    order_line_id      INTEGER,
    shipment_line_id   INTEGER,                   -- NULL until packslip layer exists (no FK on purpose)
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id)    REFERENCES receivable(invoice_id),
    FOREIGN KEY (order_id)      REFERENCES customer_order(order_id),
    FOREIGN KEY (part_id)       REFERENCES part(part_id),
    FOREIGN KEY (order_line_id) REFERENCES customer_order_line(order_line_id)
);
"""

REGISTRY = [
    ("receivable",
     "Accounts-receivable headers (customer invoice header) linked to customer orders — billing and payment status"),
    ("receivable_line",
     "AR receivable line detail extending receivable — part, order line, quantity, amount"),
]

# schema_edges join-graph rows (mirror of payables 6/7 + payable_line 27/28).
EDGES = [
    (29, "receivable",      "customer_order",      "FOREIGN_KEY", "order_id",
     "Customer invoice bills a customer order"),
    (30, "receivable_line", "receivable",          "FOREIGN_KEY", "invoice_id",
     "Invoice line belongs to a customer invoice"),
    (31, "receivable_line", "customer_order_line", "FOREIGN_KEY", "order_line_id",
     "Invoice line bills a customer order line"),
]

DUE_DAYS = 30       # net-30 terms
PAID_OFFSET = 5     # Closed orders paid 5 days before due


def fmt(d):
    return d.isoformat()


def iso(s):
    return date.fromisoformat(s[:10])


def fail(msg):
    raise SystemExit(f"[add_receivable_tables] FAIL-CLOSED: {msg}")


def run():
    print(f"DB path: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    # Phase 1 — DDL
    print("\nPhase 1 — create receivable / receivable_line ...")
    cur.executescript(DDL)

    # Phase 2 — registry + join graph
    print("Phase 2 — register in schema_nodes / schema_edges ...")
    for table_name, description in REGISTRY:
        cur.execute(
            "INSERT OR IGNORE INTO schema_nodes (table_name, table_type, description) "
            "VALUES (?, 'Table', ?)",
            (table_name, description),
        )
    for edge_id, ft, tt, rel, col, alias in EDGES:
        cur.execute(
            "INSERT OR IGNORE INTO schema_edges "
            "(edge_id, from_table, to_table, relationship_type, join_column, weight, natural_language_alias) "
            "VALUES (?,?,?,?,?,1,?)",
            (edge_id, ft, tt, rel, col, alias),
        )

    # Phase 3 — deterministic backfill (1:1 invoice per billable order)
    print("Phase 3 — backfill invoices from the order book ...")
    billable = cur.execute(
        """
        SELECT co.order_id, co.customer_name, co.status, co.completed_date,
               ROUND(SUM(ROUND(l.order_qty * l.unit_price, 2)), 2) AS billed
        FROM customer_order co
        JOIN customer_order_line l ON l.order_id = co.order_id
        WHERE co.status IN ('Closed', 'Shipped')
          AND co.completed_date IS NOT NULL
        GROUP BY co.order_id
        ORDER BY co.order_id
        """
    ).fetchall()

    # Engineered Disputed pick: highest billed value among Shipped, then order_id.
    shipped = [r for r in billable if r[2] == "Shipped"]
    disputed_order = None
    if shipped:
        disputed_order = sorted(shipped, key=lambda r: (-r[4], r[0]))[0][0]

    inserted_headers = 0
    inserted_lines = 0
    for order_id, customer, status, completed, _billed in billable:
        inv_no = f"AR-{order_id}"
        if cur.execute(
            "SELECT 1 FROM receivable WHERE invoice_number = ?", (inv_no,)
        ).fetchone():
            continue  # idempotent — already invoiced

        inv_date = iso(completed)
        due = inv_date + timedelta(days=DUE_DAYS)
        if status == "Closed":
            inv_status, pay_date = "Paid", fmt(due - timedelta(days=PAID_OFFSET))
        elif order_id == disputed_order:
            inv_status, pay_date = "Disputed", None
        else:
            inv_status, pay_date = "Open", None

        lines = cur.execute(
            """
            SELECT order_line_id, line_no, part_id, order_qty,
                   ROUND(order_qty * unit_price, 2)
            FROM customer_order_line
            WHERE order_id = ?
            ORDER BY line_no, order_line_id
            """,
            (order_id,),
        ).fetchall()
        total = round(sum(l[4] for l in lines), 2)

        cur.execute(
            """
            INSERT INTO receivable
                (order_id, customer_name, invoice_number, invoice_date,
                 due_date, amount_dollars, status, payment_date)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (order_id, customer, inv_no, fmt(inv_date), fmt(due),
             total, inv_status, pay_date),
        )
        invoice_id = cur.lastrowid
        inserted_headers += 1
        for order_line_id, line_no, part_id, qty, amount in lines:
            cur.execute(
                """
                INSERT INTO receivable_line
                    (invoice_id, line_no, order_id, part_id, qty, amount,
                     order_line_id, shipment_line_id)
                VALUES (?,?,?,?,?,?,?,NULL)
                """,
                (invoice_id, line_no, order_id, part_id, qty, amount,
                 order_line_id),
            )
            inserted_lines += 1

    conn.commit()
    print(f"  inserted {inserted_headers} invoice header(s), {inserted_lines} line(s)")

    # Phase 4 — fail-closed verify
    print("Phase 4 — fail-closed verify ...")
    got_edges = {
        (r[0], r[1], r[2]) for r in cur.execute(
            "SELECT from_table, to_table, join_column FROM schema_edges "
            "WHERE from_table IN ('receivable','receivable_line')"
        )
    }
    want_edges = {(ft, tt, col) for _eid, ft, tt, _rel, col, _a in EDGES}
    if got_edges != want_edges:
        fail(
            "schema_edges join-graph rows missing or drifted "
            f"(edge-id collision?): got {sorted(got_edges)}, want {sorted(want_edges)}"
        )
    v = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT invoice_id), COUNT(DISTINCT invoice_number) FROM receivable"
    ).fetchone()
    if not (v[0] == v[1] == v[2]):
        fail(f"invoice uniqueness violated: {v}")

    orphan = cur.execute(
        """
        SELECT COUNT(*) FROM customer_order co
        LEFT JOIN receivable r ON r.order_id = co.order_id
        WHERE co.status IN ('Closed','Shipped') AND co.completed_date IS NOT NULL
        GROUP BY co.order_id HAVING COUNT(r.invoice_id) != 1
        """
    ).fetchall()
    if orphan:
        fail(f"{len(orphan)} billable order(s) without exactly one invoice")

    leaked = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        JOIN customer_order co ON co.order_id = r.order_id
        WHERE co.status NOT IN ('Closed','Shipped')
        """
    ).fetchone()[0]
    if leaked:
        fail(f"{leaked} invoice(s) on non-billable (Open/Cancelled) orders")

    drift = cur.execute(
        """
        SELECT r.invoice_id FROM receivable r
        JOIN (SELECT invoice_id, ROUND(SUM(amount), 2) AS s
              FROM receivable_line GROUP BY invoice_id) rl
             ON rl.invoice_id = r.invoice_id
        WHERE ABS(r.amount_dollars - rl.s) > 1e-6
        """
    ).fetchall()
    if drift:
        fail(f"header != SUM(lines) for invoices {[d[0] for d in drift]}")

    lineless = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        LEFT JOIN receivable_line rl ON rl.invoice_id = r.invoice_id
        WHERE rl.receivable_line_id IS NULL
        """
    ).fetchone()[0]
    if lineless:
        fail(f"{lineless} invoice(s) with no lines")

    bad_prov = cur.execute(
        """
        SELECT COUNT(*) FROM receivable_line rl
        LEFT JOIN customer_order_line col
               ON col.order_line_id = rl.order_line_id
              AND col.order_id = rl.order_id
        WHERE col.order_line_id IS NULL
        """
    ).fetchone()[0]
    if bad_prov:
        fail(f"{bad_prov} line(s) with broken order-line provenance")

    bad_status = cur.execute(
        """
        SELECT COUNT(*) FROM receivable
        WHERE status NOT IN ('Open','Paid','Disputed','Void')
           OR (status = 'Paid' AND payment_date IS NULL)
           OR (status IN ('Open','Disputed') AND payment_date IS NOT NULL)
        """
    ).fetchone()[0]
    if bad_status:
        fail(f"{bad_status} invoice(s) with inconsistent status/payment_date")

    shipped_leak = cur.execute(
        "SELECT COUNT(*) FROM receivable_line WHERE shipment_line_id IS NOT NULL"
    ).fetchone()[0]
    if shipped_leak:
        fail(f"{shipped_leak} line(s) carry shipment_line_id before packslips exist")

    n_inv, n_line, n_open, n_paid, n_disp = cur.execute(
        """
        SELECT (SELECT COUNT(*) FROM receivable),
               (SELECT COUNT(*) FROM receivable_line),
               (SELECT COUNT(*) FROM receivable WHERE status='Open'),
               (SELECT COUNT(*) FROM receivable WHERE status='Paid'),
               (SELECT COUNT(*) FROM receivable WHERE status='Disputed')
        """
    ).fetchone()
    print(f"  VERIFY OK — {n_inv} invoices ({n_paid} Paid / {n_open} Open / "
          f"{n_disp} Disputed), {n_line} lines")
    conn.close()


if __name__ == "__main__":
    run()
