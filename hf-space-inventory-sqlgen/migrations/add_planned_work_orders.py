"""Add synthetic planned orders as unreleased work orders (WO-PLN-*).

The user asked for 30-50 synthetic planned orders, a good share of them due
more than 30 days in the future.  Per the planner's direction they are
modeled as `work_order` rows with status 'unreleased' — the real ERP
vocabulary for a planned order that MRP has proposed but no one has firmed
or released yet (see relabel_work_order_status.py for the status ladder).

Design (deterministic, idempotent, fail-closed):

- 40 planned orders WO-PLN-0001..WO-PLN-0040, workorder_type 'M'.
- Parts: MAKE-class parts with a positive lead time, EXCLUDING every part
  pinned by the MRP netting / demand-expansion migrations and tests
  (unreleased WOs count as scheduled receipts in mrp_engine, so touching a
  pinned part's grid would break those fail-closed verifies on re-run).
- Dating is anchored to the data-derived AS_OF (MAX(work_order.close_date),
  2026-01-21 — never wall-clock):
    * 12 near-term planned orders due AS_OF + 7..35 days,
    * 28 due MORE than 30 days out (AS_OF + 36..168 days), inside the
      MRP horizon's 6 monthly buckets.
  required_date = AS_OF + offset; desired_rls_date = required_date −
  part.lead_time_days (planner release anchor, mirrors the MRP grid rule).
- open_date and close_date stay NULL: a planned order has not started, and
  a NULL close_date guarantees AS_OF never moves.
- quantity is a deterministic lot: 10 + 5 * (i mod 8).
- No costs, no operations, no routings — planned orders carry no actuals.

Band contract: the demo-scale header band [10, 20] now applies to FIRM shop
orders (firmed / released / closed).  Planned (unreleased) orders are the
MRP proposal population and scale separately — the band gates in
tests/test_demand_expansion.py and expand_demand_and_completions.py are
updated in the same change to count firm orders only.

Fail-closed verify: exact WO-PLN count, all unreleased, no close/open
dates, AS_OF unchanged, >=25 planned orders due more than 30 days after
AS_OF, every part resolves and is MAKE with positive lead time, no pinned
part touched, firm-order band still [10, 20].

Run once (safe to re-run):
    cd hf-space-inventory-sqlgen
    python migrations/add_planned_work_orders.py
"""

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

N_PLANNED = 40
N_NEAR = 12                      # due within AS_OF + 7..35 days
FAR_MIN, FAR_STEP = 36, 4        # the other 28: AS_OF + 36, 40, ... (<= +144)
NEAR_MIN, NEAR_STEP = 7, 2       # near-term: AS_OF + 7, 9, ... (<= +29) then +35

# Parts whose MRP grids are pinned by existing fail-closed verifies/tests
# (add_synthetic_demand_for_netting, complete_last_week_work_orders,
# expand_demand_and_completions, test_mrp_schedule, test_demand_linkage).
PINNED_PARTS = (
    "P-10011", "P-10012", "P-10024", "P-10025", "P-10026",
    "PN-10010", "PN-10030", "PN-10040", "PN-10050", "PN-10060",
    "PN-10070", "PN-10080", "PN-10090", "PN-10100", "PN-10140",
    "PN-10150", "PN-10160", "PN-10170", "PN-10190", "PN-10200",
)


def fail(msg):
    raise SystemExit(f"[add_planned_work_orders] FAIL-CLOSED: {msg}")


def compute_as_of(cur):
    row = cur.execute("SELECT MAX(close_date) FROM work_order").fetchone()
    if not row or not row[0]:
        fail("no closed work orders — AS_OF anchor missing")
    return row[0][:10]


def run():
    print(f"DB path: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    cur = conn.cursor()

    as_of_before = compute_as_of(cur)
    as_of = date.fromisoformat(as_of_before)
    print(f"AS_OF anchor: {as_of_before}")

    # Eligible parts: MAKE, positive lead time, not pinned, deterministic order.
    ph = ",".join("?" for _ in PINNED_PARTS)
    parts = cur.execute(
        f"""
        SELECT part_id, part_description, lead_time_days
        FROM part
        WHERE part_class = 'MAKE' AND lead_time_days > 0 AND active = 1
          AND part_id NOT IN ({ph})
        ORDER BY part_id
        """,
        PINNED_PARTS,
    ).fetchall()
    if len(parts) < 1:
        fail("no eligible MAKE parts with positive lead time")
    print(f"eligible parts: {len(parts)} (cycling deterministically)")

    # Deterministic due-date offsets: first N_NEAR near-term, rest far-out.
    offsets = [NEAR_MIN + NEAR_STEP * i for i in range(N_NEAR)]          # 7..29,31,33? cap below
    offsets = [min(o, 35) for o in offsets]
    offsets += [FAR_MIN + FAR_STEP * i for i in range(N_PLANNED - N_NEAR)]  # 36..144

    inserted = 0
    for i in range(N_PLANNED):
        wo_id = f"WO-PLN-{i + 1:04d}"
        if cur.execute("SELECT 1 FROM work_order WHERE wo_id=?", (wo_id,)).fetchone():
            continue  # idempotent
        part_id, part_desc, lead = parts[i % len(parts)]
        due = as_of + timedelta(days=offsets[i])
        rls = due - timedelta(days=int(lead))
        qty = 10 + 5 * (i % 8)
        cur.execute(
            """
            INSERT INTO work_order
                (wo_id, workorder_type, part_id, part_description, quantity,
                 status, open_date, close_date, required_date,
                 desired_rls_date, site_id)
            VALUES (?, 'M', ?, ?, ?, 'unreleased', NULL, NULL, ?, ?, 'SITE-1')
            """,
            (wo_id, part_id, part_desc, qty, due.isoformat(), rls.isoformat()),
        )
        inserted += 1
    conn.commit()
    print(f"inserted {inserted} planned order(s)")

    # ── Fail-closed verify ─────────────────────────────────────────────────
    print("verify ...")
    if compute_as_of(cur) != as_of_before:
        fail(f"AS_OF moved from {as_of_before}")

    n, n_unrel, n_dated = cur.execute(
        """
        SELECT COUNT(*),
               SUM(status = 'unreleased'),
               SUM(close_date IS NULL AND open_date IS NULL
                   AND required_date IS NOT NULL)
        FROM work_order WHERE wo_id LIKE 'WO-PLN-%'
        """
    ).fetchone()
    if n != N_PLANNED:
        fail(f"expected {N_PLANNED} WO-PLN planned orders, found {n}")
    if n_unrel != n or n_dated != n:
        fail(f"planned-order shape drift: unreleased={n_unrel}, clean-dated={n_dated} of {n}")

    beyond_30 = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE wo_id LIKE 'WO-PLN-%' "
        "AND date(required_date) > date(?, '+30 days')",
        (as_of_before,),
    ).fetchone()[0]
    if beyond_30 < 25:
        fail(f"only {beyond_30} planned orders due more than 30 days out (want >= 25)")

    bad_part = cur.execute(
        f"""
        SELECT COUNT(*) FROM work_order w
        LEFT JOIN part p ON p.part_id = w.part_id
        WHERE w.wo_id LIKE 'WO-PLN-%'
          AND (p.part_id IS NULL OR p.part_class != 'MAKE'
               OR p.lead_time_days <= 0 OR w.part_id IN ({ph}))
        """,
        PINNED_PARTS,
    ).fetchone()[0]
    if bad_part:
        fail(f"{bad_part} planned order(s) on ineligible or pinned parts")

    firm = cur.execute(
        "SELECT COUNT(*) FROM work_order WHERE status IN ('firmed','released','closed')"
    ).fetchone()[0]
    if not (10 <= firm <= 20):
        fail(f"firm work-order headers out of band: {firm}")

    print(f"  VERIFY OK — {n} planned orders ({beyond_30} due >30 days after AS_OF), "
          f"firm WO band = {firm}")
    conn.close()


if __name__ == "__main__":
    run()
