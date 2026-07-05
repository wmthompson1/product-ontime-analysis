"""
Migration: create the EMPLOYEE master table (~300 synthetic employees, 10 of
them buyers) and add part.buyer_code to the parts master.

Why: the semantic layer has always carried an EMPLOYEE table node ("Employee
master records") with no physical table behind it — labor tickets reference
employee_id strings that resolve to nothing. Management asked for a synthetic
workforce: ~300 employees with plant-worker cost at $40–$45/hr, ~10 buyers who
buy parts, and a buyer field on the parts master.

Everything is DETERMINISTIC and GROUNDED to existing ERP data (no randomness):

  EMPLOYEE (300 rows, EMP-001 .. EMP-300)
    - The 15 employee_ids already present in labor_ticket keep their IDs and
      are plant workers; their home_resource_id is the shop resource they have
      the MOST labor tickets against (tie-break: alphabetical resource_id).
    - Remaining plant workers are assigned home resources round-robin across
      the real machine/labor resources (type M/L, never OUTSIDE/S).
    - Job title + department derive from the home resource's description
      (Machinist / Welder / Assembler / Inspector ...).
    - Plant-worker hourly_rate = 40.00 + ((n*8) % 21) * 0.25  ->  [40.00, 45.00]
    - EMP-291..EMP-300 are the 10 buyers (BUYER-1..BUYER-10), dept Purchasing,
      hourly_rate = 44.00 + ((n*3) % 17) * 0.25  ->  [44.00, 48.00]
    - hire_date = 2015-01-05 + ((n*89) % 3280) days -> all before the first
      labor ticket (2024-01-22), checked fail-closed.
    - Names come from fixed lists indexed by employee number (unique combos).

  Buyer <-> supplier ownership
    - Suppliers ordered by (lower(category), supplier_id) and dealt
      round-robin to BUYER-1..BUYER-10, so each buyer owns a category-coherent
      slice of the supply base.

  part.buyer_code (parts master buyer field)
    - For every part with PO history: buyer of the supplier the part was most
      purchased from (MAX total line value; tie-break supplier_id). Parts with
      no PO history (in-house MAKE parts) stay NULL — nobody buys them.

  purchase_order.buyer_id
    - Reassigned from the flat 'BUYER-1' to the buyer who owns the PO's
      supplier. Every PO has a valid supplier (verified), so every PO lands on
      a real buyer.

Run once (idempotent / safe to re-run — all derivations are deterministic):
    cd hf-space-inventory-sqlgen
    python migrations/add_employees_and_buyers.py
"""

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

TOTAL_EMPLOYEES = 300
BUYER_COUNT = 10
FIRST_BUYER_N = TOTAL_EMPLOYEES - BUYER_COUNT + 1  # EMP-291

EMPLOYEE_DDL = """
CREATE TABLE IF NOT EXISTS EMPLOYEE (
    employee_id      TEXT PRIMARY KEY,           -- e.g. EMP-001
    employee_name    TEXT NOT NULL,
    job_title        TEXT NOT NULL,
    department       TEXT NOT NULL,
    hourly_rate      REAL NOT NULL DEFAULT 0.0,  -- plant workers 40.00-45.00
    buyer_code       TEXT UNIQUE,                -- BUYER-1..BUYER-10, NULL for non-buyers
    home_resource_id TEXT,                       -- shop_resource the worker mans (NULL for buyers)
    hire_date        DATE,
    active           INTEGER DEFAULT 1,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

FIRST_NAMES = [
    "James", "Maria", "Robert", "Linda", "Michael", "Patricia", "David",
    "Jennifer", "William", "Elizabeth", "Richard", "Barbara", "Joseph",
    "Susan", "Thomas", "Jessica", "Carlos", "Sarah", "Daniel", "Karen",
    "Matthew", "Nancy", "Anthony", "Lisa", "Mark",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson",
]


def employee_name(n: int) -> str:
    first = FIRST_NAMES[(n - 1) % len(FIRST_NAMES)]
    last = LAST_NAMES[((n - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
    return f"{first} {last}"


def plant_rate(n: int) -> float:
    # 8 is coprime to 21, so (n*8) % 21 walks every step 0..20 and the
    # rate band covers the full $40.00-$45.00 in $0.25 increments.
    return round(40.00 + ((n * 8) % 21) * 0.25, 2)


def buyer_rate(n: int) -> float:
    return round(44.00 + ((n * 3) % 17) * 0.25, 2)


def hire_date_for(n: int) -> str:
    return (date(2015, 1, 5) + timedelta(days=(n * 89) % 3280)).isoformat()


def title_dept_for_resource(resource_id: str, description: str) -> tuple[str, str]:
    """Derive job title + department from the home resource, keyword-grounded
    to the shop_resource description (the same text the routing uses)."""
    d = (description or "").lower()
    r = resource_id.upper()
    if "weld" in d or r.startswith("WELD"):
        return "Welder", "Welding"
    if "inspect" in d or "quality" in d or "cmm" in d:
        return "Quality Inspector", "Quality"
    if "assembly" in d or r.startswith("ASSEM"):
        return "Assembly Technician", "Assembly"
    # Mills, lathes, drills, waterjet, machinist labor grades — the machine shop.
    return "CNC Machinist", "Machining"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # ------------------------------------------------------------------
        # 1. EMPLOYEE table (create if missing) + part.buyer_code column
        # ------------------------------------------------------------------
        cur.execute(EMPLOYEE_DDL)

        part_cols = {row[1] for row in cur.execute("PRAGMA table_info(part)")}
        if "buyer_code" not in part_cols:
            cur.execute("ALTER TABLE part ADD COLUMN buyer_code TEXT")
            print("Added column part.buyer_code")
        else:
            print("Column part.buyer_code already exists — skipping add")

        # ------------------------------------------------------------------
        # 2. Grounding data from the live ERP
        # ------------------------------------------------------------------
        # Home resource for ticketed employees: their most-used resource.
        ticketed_home: dict[str, str] = {}
        for row in cur.execute(
            "SELECT employee_id, resource_id, COUNT(*) AS c FROM labor_ticket "
            "GROUP BY employee_id, resource_id "
            "ORDER BY employee_id, c DESC, resource_id"
        ):
            ticketed_home.setdefault(row["employee_id"], row["resource_id"])

        # Real plant resources (machines + labor grades; never outside services).
        resources = list(
            cur.execute(
                "SELECT resource_id, description FROM shop_resource "
                "WHERE resource_type IN ('M','L') AND resource_id != 'OUTSIDE' "
                "ORDER BY resource_id"
            )
        )
        if not resources:
            raise RuntimeError("No M/L shop resources found — cannot ground plant workers")
        resource_desc = {r["resource_id"]: r["description"] for r in resources}

        # ------------------------------------------------------------------
        # 3. Insert 300 employees (INSERT OR IGNORE — idempotent)
        # ------------------------------------------------------------------
        inserted = 0
        rr = 0  # round-robin cursor over resources for non-ticketed workers
        for n in range(1, TOTAL_EMPLOYEES + 1):
            emp_id = f"EMP-{n:03d}"
            if n >= FIRST_BUYER_N:
                buyer_code = f"BUYER-{n - FIRST_BUYER_N + 1}"
                row = (
                    emp_id, employee_name(n), "Buyer", "Purchasing",
                    buyer_rate(n), buyer_code, None, hire_date_for(n),
                )
            else:
                if emp_id in ticketed_home:
                    home = ticketed_home[emp_id]
                else:
                    home = resources[rr % len(resources)]["resource_id"]
                    rr += 1
                title, dept = title_dept_for_resource(home, resource_desc.get(home, ""))
                row = (
                    emp_id, employee_name(n), title, dept,
                    plant_rate(n), None, home, hire_date_for(n),
                )
            cur.execute(
                "INSERT INTO EMPLOYEE "
                "(employee_id, employee_name, job_title, department, hourly_rate,"
                " buyer_code, home_resource_id, hire_date) VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(employee_id) DO UPDATE SET "
                "employee_name=excluded.employee_name, job_title=excluded.job_title, "
                "department=excluded.department, hourly_rate=excluded.hourly_rate, "
                "buyer_code=excluded.buyer_code, home_resource_id=excluded.home_resource_id, "
                "hire_date=excluded.hire_date",
                row,
            )
            inserted += cur.rowcount
        print(f"Inserted {inserted} employees (of {TOTAL_EMPLOYEES})")

        # ------------------------------------------------------------------
        # 4. Buyer <-> supplier ownership (deterministic round-robin by category)
        # ------------------------------------------------------------------
        suppliers = [
            r["supplier_id"]
            for r in cur.execute(
                "SELECT supplier_id FROM suppliers "
                "ORDER BY lower(COALESCE(category,'')), supplier_id"
            )
        ]
        supplier_buyer = {
            sid: f"BUYER-{(i % BUYER_COUNT) + 1}" for i, sid in enumerate(suppliers)
        }

        # ------------------------------------------------------------------
        # 5. purchase_order.buyer_id = buyer who owns the PO's supplier
        # ------------------------------------------------------------------
        po_updates = 0
        # fetchall() first: updating through the cursor that is still
        # iterating a SELECT silently truncates the iteration.
        for row in cur.execute("SELECT po_id, supplier_id FROM purchase_order").fetchall():
            buyer = supplier_buyer.get(row["supplier_id"])
            if buyer is None:
                raise RuntimeError(
                    f"PO {row['po_id']} references unknown supplier {row['supplier_id']}"
                )
            cur.execute(
                "UPDATE purchase_order SET buyer_id = ? "
                "WHERE po_id = ? AND (buyer_id IS NULL OR buyer_id != ?)",
                (buyer, row["po_id"], buyer),
            )
            po_updates += cur.rowcount
        print(f"Reassigned buyer_id on {po_updates} purchase orders")

        # ------------------------------------------------------------------
        # 6. part.buyer_code = buyer of the supplier the part is most bought
        #    from (MAX total line value, tie-break supplier_id). No PO history
        #    -> NULL (in-house parts are not bought).
        # ------------------------------------------------------------------
        part_supplier: dict[str, str] = {}
        for row in cur.execute(
            "SELECT l.part_id, po.supplier_id, SUM(l.line_total) AS total "
            "FROM po_line l JOIN purchase_order po ON po.po_id = l.po_id "
            "JOIN part p ON p.part_id = l.part_id "
            "GROUP BY l.part_id, po.supplier_id "
            "ORDER BY l.part_id, total DESC, po.supplier_id"
        ):
            part_supplier.setdefault(row["part_id"], row["supplier_id"])

        part_updates = 0
        for part_id, sid in part_supplier.items():
            cur.execute(
                "UPDATE part SET buyer_code = ? WHERE part_id = ?",
                (supplier_buyer[sid], part_id),
            )
            part_updates += cur.rowcount
        if part_supplier:
            cur.execute(
                "UPDATE part SET buyer_code = NULL WHERE part_id NOT IN ({})".format(
                    ",".join("?" * len(part_supplier))
                ),
                list(part_supplier.keys()),
            )
        else:
            raise RuntimeError(
                "No PO history found for any part — refusing to assign buyer codes"
            )
        print(f"Assigned buyer_code on {part_updates} parts "
              f"({cur.rowcount} in-house parts left NULL)")

        # ------------------------------------------------------------------
        # 7. Fail-closed verification
        # ------------------------------------------------------------------
        total = cur.execute("SELECT COUNT(*) FROM EMPLOYEE").fetchone()[0]
        if total != TOTAL_EMPLOYEES:
            raise RuntimeError(f"EMPLOYEE has {total} rows, expected {TOTAL_EMPLOYEES}")

        orphans = cur.execute(
            "SELECT COUNT(DISTINCT employee_id) FROM labor_ticket "
            "WHERE employee_id NOT IN (SELECT employee_id FROM EMPLOYEE)"
        ).fetchone()[0]
        if orphans:
            raise RuntimeError(f"{orphans} labor-ticket employees missing from EMPLOYEE")

        bad_rate = cur.execute(
            "SELECT COUNT(*) FROM EMPLOYEE WHERE buyer_code IS NULL "
            "AND (hourly_rate < 40.0 OR hourly_rate > 45.0)"
        ).fetchone()[0]
        if bad_rate:
            raise RuntimeError(f"{bad_rate} plant workers outside the $40-$45 band")

        buyers = cur.execute(
            "SELECT COUNT(*) FROM EMPLOYEE WHERE buyer_code IS NOT NULL"
        ).fetchone()[0]
        if buyers != BUYER_COUNT:
            raise RuntimeError(f"{buyers} buyers found, expected {BUYER_COUNT}")

        bad_po = cur.execute(
            "SELECT COUNT(*) FROM purchase_order "
            "WHERE buyer_id IS NULL OR buyer_id NOT IN "
            "(SELECT buyer_code FROM EMPLOYEE WHERE buyer_code IS NOT NULL)"
        ).fetchone()[0]
        if bad_po:
            raise RuntimeError(f"{bad_po} POs carry a buyer_id that is not a real buyer")

        unbought = cur.execute(
            "SELECT COUNT(*) FROM part WHERE buyer_code IS NULL "
            "AND part_id IN (SELECT part_id FROM po_line)"
        ).fetchone()[0]
        if unbought:
            raise RuntimeError(f"{unbought} parts with PO history have no buyer_code")

        late_hire = cur.execute(
            "SELECT COUNT(*) FROM EMPLOYEE e JOIN labor_ticket t USING (employee_id) "
            "WHERE e.hire_date >= t.clock_in"
        ).fetchone()[0]
        if late_hire:
            raise RuntimeError(f"{late_hire} labor tickets predate the worker's hire_date")

        conn.commit()

        # ------------------------------------------------------------------
        # 8. Summary
        # ------------------------------------------------------------------
        print("\nWorkforce summary:")
        for dept, n, lo, hi in cur.execute(
            "SELECT department, COUNT(*), MIN(hourly_rate), MAX(hourly_rate) "
            "FROM EMPLOYEE GROUP BY department ORDER BY department"
        ):
            print(f"  {dept:<12} {n:>3} employees  rate ${lo:.2f}-${hi:.2f}")
        print("\nBuyer workload:")
        for code, pos, parts in cur.execute(
            "SELECT e.buyer_code, "
            "  (SELECT COUNT(*) FROM purchase_order po WHERE po.buyer_id = e.buyer_code), "
            "  (SELECT COUNT(*) FROM part p WHERE p.buyer_code = e.buyer_code) "
            "FROM EMPLOYEE e WHERE e.buyer_code IS NOT NULL ORDER BY LENGTH(e.buyer_code), e.buyer_code"
        ):
            print(f"  {code:<9} {pos:>3} POs  {parts:>2} parts")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
