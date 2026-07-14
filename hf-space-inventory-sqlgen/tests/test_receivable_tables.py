"""Gate test — physical AR ledger (receivable / receivable_line).

Locks the invariants of migrations/add_receivable_tables.py:
  - both tables exist, registered in schema_nodes, with declared FKs;
  - schema_edges join-graph rows present (mirror of the payables precedent);
  - 1:1 invoicing: every billable (Closed/Shipped, completed) order has
    exactly one invoice; Open/Cancelled orders have none;
  - header amount == SUM(line amounts); every invoice has lines;
  - line provenance resolves to a real customer_order_line of the same order;
  - status semantics: Closed->Paid (payment_date set), Shipped->Open or the
    single engineered Disputed (payment_date NULL); vocabulary respected;
  - shipment_line_id NULL everywhere (packslip placeholder contract);
  - dates are data-derived: invoice_date == the order's completed_date,
    due_date == invoice_date + 30 days.

Run gate-style:
    cd hf-space-inventory-sqlgen
    python tests/test_receivable_tables.py
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

FAILURES = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1 — tables + registry
    tables = {
        r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('receivable','receivable_line')"
        )
    }
    check("tables exist", tables == {"receivable", "receivable_line"}, str(tables))

    reg = {
        r[0] for r in cur.execute(
            "SELECT table_name FROM schema_nodes "
            "WHERE table_name IN ('receivable','receivable_line')"
        )
    }
    check("schema_nodes registered", reg == {"receivable", "receivable_line"}, str(reg))

    # 2 — declared FKs (exporter mints references edges from these)
    fks_r = {(f[2], f[3]) for f in cur.execute("PRAGMA foreign_key_list(receivable)")}
    check("receivable FK -> customer_order", ("customer_order", "order_id") in fks_r, str(fks_r))
    fks_l = {(f[2], f[3]) for f in cur.execute("PRAGMA foreign_key_list(receivable_line)")}
    for want in [("receivable", "invoice_id"),
                 ("customer_order", "order_id"),
                 ("part", "part_id"),
                 ("customer_order_line", "order_line_id")]:
        check(f"receivable_line FK -> {want[0]}.{want[1]}", want in fks_l, str(fks_l))
    check("no FK declared on shipment_line_id (packslips absent)",
          not any(f[3] == "shipment_line_id"
                  for f in cur.execute("PRAGMA foreign_key_list(receivable_line)")))

    # 3 — schema_edges join graph
    edges = {
        (r[0], r[1], r[2]) for r in cur.execute(
            "SELECT from_table, to_table, join_column FROM schema_edges "
            "WHERE from_table IN ('receivable','receivable_line')"
        )
    }
    for want in [("receivable", "customer_order", "order_id"),
                 ("receivable_line", "receivable", "invoice_id"),
                 ("receivable_line", "customer_order_line", "order_line_id")]:
        check(f"schema_edge {want[0]} -> {want[1]}", want in edges, str(edges))

    # 4 — 1:1 invoicing coverage
    bad_cov = cur.execute(
        """
        SELECT co.order_id, COUNT(r.invoice_id) FROM customer_order co
        LEFT JOIN receivable r ON r.order_id = co.order_id
        WHERE co.status IN ('Closed','Shipped') AND co.completed_date IS NOT NULL
        GROUP BY co.order_id HAVING COUNT(r.invoice_id) != 1
        """
    ).fetchall()
    check("every billable order has exactly one invoice", not bad_cov, str(bad_cov))

    leaked = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        JOIN customer_order co ON co.order_id = r.order_id
        WHERE co.status NOT IN ('Closed','Shipped')
        """
    ).fetchone()[0]
    check("no invoices on Open/Cancelled orders", leaked == 0, str(leaked))

    uniq = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT invoice_number) FROM receivable"
    ).fetchone()
    check("invoice_number unique", uniq[0] == uniq[1] and uniq[0] > 0, str(uniq))

    # 5 — amounts + lines
    drift = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        JOIN (SELECT invoice_id, ROUND(SUM(amount),2) s
              FROM receivable_line GROUP BY invoice_id) rl
             ON rl.invoice_id = r.invoice_id
        WHERE ABS(r.amount_dollars - rl.s) > 1e-6
        """
    ).fetchone()[0]
    check("header amount == SUM(lines)", drift == 0, str(drift))

    lineless = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        LEFT JOIN receivable_line rl ON rl.invoice_id = r.invoice_id
        WHERE rl.receivable_line_id IS NULL
        """
    ).fetchone()[0]
    check("no line-less invoices", lineless == 0, str(lineless))

    bad_prov = cur.execute(
        """
        SELECT COUNT(*) FROM receivable_line rl
        LEFT JOIN customer_order_line col
               ON col.order_line_id = rl.order_line_id
              AND col.order_id = rl.order_id
        WHERE col.order_line_id IS NULL
        """
    ).fetchone()[0]
    check("line provenance resolves to same-order order_line", bad_prov == 0, str(bad_prov))

    # 6 — status semantics
    bad_status = cur.execute(
        """
        SELECT COUNT(*) FROM receivable
        WHERE status NOT IN ('Open','Paid','Disputed','Void')
           OR (status = 'Paid' AND payment_date IS NULL)
           OR (status IN ('Open','Disputed') AND payment_date IS NOT NULL)
        """
    ).fetchone()[0]
    check("status/payment_date semantics", bad_status == 0, str(bad_status))

    closed_not_paid = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        JOIN customer_order co ON co.order_id = r.order_id
        WHERE co.status = 'Closed' AND r.status != 'Paid'
        """
    ).fetchone()[0]
    check("Closed orders invoiced as Paid", closed_not_paid == 0, str(closed_not_paid))

    n_disputed = cur.execute(
        "SELECT COUNT(*) FROM receivable WHERE status='Disputed'"
    ).fetchone()[0]
    check("exactly one engineered Disputed invoice", n_disputed == 1, str(n_disputed))

    placeholder = cur.execute(
        "SELECT COUNT(*) FROM receivable_line WHERE shipment_line_id IS NOT NULL"
    ).fetchone()[0]
    check("shipment_line_id NULL everywhere", placeholder == 0, str(placeholder))

    # 7 — data-derived dating
    bad_dates = cur.execute(
        """
        SELECT COUNT(*) FROM receivable r
        JOIN customer_order co ON co.order_id = r.order_id
        WHERE DATE(r.invoice_date) != DATE(co.completed_date)
           OR DATE(r.due_date) != DATE(r.invoice_date, '+30 days')
        """
    ).fetchone()[0]
    check("invoice_date == completed_date and due_date == +30d", bad_dates == 0, str(bad_dates))

    conn.close()
    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
