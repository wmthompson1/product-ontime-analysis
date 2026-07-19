"""One-command database bootstrap for a fresh clone.

manufacturing.db is intentionally gitignored, so a fresh clone (or a fresh
Replit / Hugging Face copy) has no database. This script rebuilds the whole
thing deterministically:

    cd hf-space-inventory-sqlgen && python scripts/bootstrap_db.py

Steps (all idempotent — safe to re-run on an existing DB):
  1. Apply app_schema/schema_sqlite.sql if the DB is missing (core ERP +
     semantic-layer tables and reference seeds).
  2. Run the structural migrations that own tables/columns NOT in
     schema_sqlite.sql (wave-4 traceability spine, employees/buyers, ...).
  3. Seed synthetic ERP data (scripts/seed_erp_synthetic.py).
  4. Run the documented high-fidelity backfill chain in its required order
     (see the seed_erp_synthetic.py docstring).
  5. Build the MRP demand/supply foundation.
  6. Prune to demo scale (15 CO / 15 WO / 15-20 PO band).
  7. Split receiving into header + line and broaden the commodity mix.
  8. Link work orders to their customer-order demand lines (>= 50%), set
     safety stock (= 1), and seed the forecast demand source.
  9. Verify the MRP tab has planning parts and can compute a grid —
     fail closed if not.

Everything is plain SQLite — no ArangoDB, no API keys, no network needed.
"""

import os
import sqlite3
import subprocess
import sys
import time

HF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
SCHEMA_SQL = os.path.join(HF_DIR, "app_schema", "schema_sqlite.sql")

# (relative script path, args) — order matters.
STEPS = [
    # rename first: existing DBs still carrying invoice_header get the
    # payables name before anything downstream reads or writes it
    # (no-op on a fresh DB built from the updated schema_sqlite.sql)
    ("migrations/rename_invoice_header_to_payables.py", []),
    # structural migrations first: tables the seeder writes into
    ("migrations/add_wave4_traceability_tables.py", []),
    # synthetic ERP data
    ("scripts/seed_erp_synthetic.py", []),
    # structural migrations that ground themselves in seeded data
    ("migrations/add_employees_and_buyers.py", []),
    ("migrations/add_warehouse_part_location.py", []),
    ("migrations/add_supplier_payables_wiring.py", []),
    ("migrations/add_receivables_wiring.py", []),
    ("migrations/add_customer_order_completed_date.py", []),
    # documented high-fidelity chain (order is mandatory)
    ("migrations/add_operation_type.py", []),
    ("migrations/regap_and_seed_requirements.py", []),
    ("migrations/relabel_work_order_status.py", []),
    ("migrations/backfill_operation_progress.py", []),
    ("migrations/backfill_operation_schedule.py", []),
    ("migrations/backfill_supplier_rating_and_wo_actuals.py", []),
    ("migrations/backfill_operation_actuals.py", []),
    ("migrations/backfill_labor_chain.py", []),
    # planner master data + MRP foundation
    ("migrations/backfill_pn_parts_master_and_planner.py", []),
    ("migrations/backfill_mrp_demand_supply.py", []),
    # demo scale + receiving line split / commodity mix
    ("migrations/prune_erp_to_demo_scale.py", []),
    ("migrations/add_receiving_line_and_commodities.py", []),
    # 100+ plannable parts for the MRP dropdown (runs LAST: after the prune so
    # the demo-scale trim never sees — or removes — the expansion rows)
    ("migrations/expand_mrp_part_universe.py", []),
    # demand linkage (WO -> customer_order_line, >=50%), safety stock, forecast
    # demand source (runs after the expansion so its WOs/CO lines participate)
    ("migrations/add_demand_linkage_and_forecast.py", []),
    # complete the PO <-> receiver <-> payable three-way match chain (runs
    # after the prune + receiving-line split so it sees the final PO set;
    # never touches MRP-critical POs)
    ("migrations/complete_three_way_match.py", []),
    # demand-side expansion: close three shop orders (finished goods to
    # stock), repair outside-service op keys, re-run the cost cascade, and
    # add three Open customer orders whose lines make every stocked MAKE
    # part a planning part (runs after the three-way match completion so
    # received service POs accrue onto their operations)
    ("migrations/expand_demand_and_completions.py", []),
    # last-week completions: close three more in-progress shop orders inside the
    # 7-day window ending on AS_OF (2026-01-21), receipt their finished goods to
    # stock as synthetic supply, and re-run the cost/labor cascade. Headers stay
    # at 20; AS_OF never moves. Runs after expand_demand_and_completions so it
    # sees the same closed baseline.
    ("migrations/complete_last_week_work_orders.py", []),
    # synthetic demand so planned orders visibly net against on-hand: adds open
    # customer-order demand lines (scale via LINES, headers stay at 20; AS_OF
    # never moves) for the parts whose on-hand the completions boosted, sized
    # above on-hand so the grid draws PAB down to safety stock and then plans
    # the shortfall. Runs after the completions so it sees the boosted on-hand.
    ("migrations/add_synthetic_demand_for_netting.py", []),
    # add the physical receiving.received_date column (dock-arrival date, the
    # noun the Temporal Parameter Contract's Horizon Filter binds to) and
    # backfill it = receipt_date. Runs BEFORE the uninvoiced-receipts demo so
    # its governed-view verify (which now filters on received_date) resolves the
    # column, and AFTER every earlier receiving insert so the backfill is total.
    ("migrations/add_received_date.py", []),
    # uninvoiced-receipts exception populations for the governed 3WM view
    # payables_uninvoicedreceipts (runs after the match completion so the
    # engineered exceptions are never "repaired" back into a clean ledger)
    ("migrations/add_uninvoiced_receipts_demo.py", []),
    # partial-receipt accrual exposure populations for the governed PRA view
    # payables_partialreceiptaccrual (adds engineered PO LINES — never headers —
    # partially received and under/never vouchered; runs after the uninvoiced
    # demo so both exception families coexist without repair)
    ("migrations/add_partial_receipt_accrual_demo.py", []),
    # wire the consolidated Three-Way Match Coverage spine into the Query
    # Palette (selector wiring only — no data writes; runs after the PRA demo
    # so its fail-closed verify sees all five match states in the population)
    ("migrations/add_twm_coverage_palette.py", []),
    # synthetic planned orders: 40 unreleased work orders (WO-PLN-*) on
    # non-pinned MAKE parts, most due >30 days after AS_OF; the firm-order
    # band [10,20] excludes them (planned orders scale separately). Runs
    # after the netting demo so its pinned-grid verifies never see them.
    ("migrations/add_planned_work_orders.py", []),
    # physical AR ledger: receivable / receivable_line tables + deterministic
    # invoice backfill from the final order book (runs after every migration
    # that adds or prunes customer orders so the 1:1 invoicing sees the
    # finished demand side; Open orders stay uninvoiced by design)
    ("migrations/add_receivable_tables.py", []),
    # minimal synthetic GL ledger tables (gl_events + RM/WIP/FG inventory +
    # job cost detail) — DDL only, idempotent; posting/population is a later
    # task. job_id links structurally to work_order.wo_id.
    ("migrations/add_gl_ledger_tables.py", []),
    # re-declare structural FKs the frozen graph records but fresh DDL lacks
    # (declared-FK-only consumers like metric assembly fail closed without them;
    # runs last so every table in the graph already exists)
    ("migrations/declare_structural_fks.py", []),
]

# The MRP Schedule dropdown (open in-horizon demand parts) must list at least
# this many parts after a full bootstrap (expand_mrp_part_universe.py).
MIN_MRP_PLANNING_PARTS = 100


def init_schema_if_missing():
    if os.path.exists(DB_PATH):
        print(f"[bootstrap] DB exists at {DB_PATH} — skipping schema init")
        return
    print(f"[bootstrap] creating fresh DB from schema_sqlite.sql")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        with open(SCHEMA_SQL) as f:
            conn.executescript(f.read())
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        print(f"[bootstrap] schema applied — {n} tables")
    finally:
        conn.close()


def run_steps():
    for rel, args in STEPS:
        path = os.path.join(HF_DIR, rel)
        if not os.path.exists(path):
            raise SystemExit(f"[bootstrap] FAIL-CLOSED: missing script {rel}")
        t0 = time.time()
        print(f"[bootstrap] → {rel}")
        r = subprocess.run([sys.executable, path, *args], cwd=HF_DIR)
        if r.returncode != 0:
            raise SystemExit(
                f"[bootstrap] FAIL-CLOSED: {rel} exited {r.returncode} — "
                "fix the error above and re-run (all steps are idempotent)."
            )
        print(f"[bootstrap]   done in {time.time() - t0:.1f}s")


def verify_mrp():
    print("[bootstrap] verifying MRP readiness…")
    sys.path.insert(0, HF_DIR)
    import mrp_engine as mrp

    conn = sqlite3.connect(DB_PATH)
    try:
        mrp.validate_planning_inputs(conn)
        parts = mrp.list_planning_parts(conn)
        if not parts:
            raise SystemExit(
                "[bootstrap] FAIL-CLOSED: MRP has no planning parts "
                "(no open demand in the horizon)."
            )
        if len(parts) < MIN_MRP_PLANNING_PARTS:
            raise SystemExit(
                f"[bootstrap] FAIL-CLOSED: MRP dropdown must list at least "
                f"{MIN_MRP_PLANNING_PARTS} planning parts, got {len(parts)} "
                "(expand_mrp_part_universe.py did not take effect)."
            )
        p0 = parts[0]
        if isinstance(p0, dict):
            first = p0["part_id"]
        elif isinstance(p0, (tuple, list)):
            first = p0[0]
        else:
            first = p0
        grid = mrp.compute_mrp_grid(conn, first)
        if not grid:
            raise SystemExit(
                f"[bootstrap] FAIL-CLOSED: empty MRP grid for {first}"
            )
        print(f"[bootstrap] MRP OK — {len(parts)} planning part(s); "
              f"grid computed for {first}")
    finally:
        conn.close()


def main():
    t0 = time.time()
    init_schema_if_missing()
    run_steps()
    verify_mrp()
    print(f"[bootstrap] complete in {time.time() - t0:.1f}s — "
          "start the app with: PORT=5000 python app.py")


if __name__ == "__main__":
    main()
