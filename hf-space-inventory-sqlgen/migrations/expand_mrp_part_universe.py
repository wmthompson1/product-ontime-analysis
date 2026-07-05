"""
Migration: expand the synthetic part universe so the MRP dropdown lists 100+
plannable parts.

Why (the MRP Schedule tab only lists parts with open in-horizon demand, and the
demo-scale data foundation left just 2 such parts):
  - the part master held 55 parts, but only one customer order was still Open
    (2 lines / 2 distinct parts), so the dropdown had 2 entries;
  - a believable plant demo needs 100+ selectable parts, each computing a valid
    fail-closed MRP grid.

What this migration establishes (all synthetic, SQLite-only, deterministic):
  1. 100 new aerospace-flavored parts (MCH-5xxxx MAKE, AVN-5xxxx BUY,
     HDW-5xxxx HARDWARE, RMT-5xxxx RAW, OSP-5xxxx OUTSIDE_SERVICE), each with a
     positive lead time, positive on-hand stock, planner/buyer ownership and
     commodity codes consistent with the existing masters.
  2. Two new OPEN customer orders (CO-MRP-001/002) carrying one line per new
     part, so all 100 parts have open demand. need_by_date is recomputed every
     run with the EXACT formula backfill_mrp_demand_supply uses
     (crc32("col:<order_line_id>", as_of)), so a later backfill re-run is a
     no-op on these rows and the two migrations stay in lockstep.
  3. A real supply basis for every part:
       - every new part carries positive on-hand stock (a real supply basis per
         mrp_engine.validate_planning_inputs);
       - all buy-side parts (BUY / HARDWARE / RAW / OUTSIDE_SERVICE) also get an
         open scheduled receipt via three consolidated block POs
         (PO-MRP-BLK1..3, many lines each — consolidation keeps the PO count
         inside the demo-scale prune band [10, 25]);
       - the first five MAKE parts also get open work orders (WO-MRP-001..005;
         five keeps work_order inside its prune band [10, 20]).

Demo-scale bands: prune_erp_to_demo_scale skips trimming when CO/WO/PO counts
are already inside [10, 20] / [10, 20] / [10, 25]. This migration adds only
2 CO + 5 WO + 3 PO headers, so the bands still hold afterwards and re-running
the bootstrap chain never prunes these rows. This is asserted fail-closed below.

Anchor (data-derived, never wall-clock): as_of = MAX(work_order.close_date)
(mrp_engine.compute_as_of). The new WOs are open (close_date NULL) so the
anchor is a fixed point. All dates derive from as_of via crc32 of stable keys.

Idempotency: parts / orders / POs / WOs use INSERT OR IGNORE on their natural
PKs; order lines and PO lines are guarded by NOT EXISTS on (order, part);
need_by/desired_release are pure functions of stable keys, recomputed to the
same value every run. Safe to re-run with an identical result. The certified
ArangoDB graph is never touched. Ends with the fail-closed planning validation
plus sample grid computations.

Run order: LAST in the bootstrap chain (after prune_erp_to_demo_scale and
add_receiving_line_and_commodities, so the prune never sees — and never has to
preserve — this expansion). Safe to re-run.
    cd hf-space-inventory-sqlgen
    python migrations/expand_mrp_part_universe.py
"""

import os
import sqlite3
import sys
import zlib
from datetime import timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_HERE)
sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _HERE)

import mrp_engine as eng  # noqa: E402
from backfill_mrp_demand_supply import _horizon_date  # noqa: E402  (exact date formula lockstep)

DB_PATH = os.path.join(_APP_DIR, "app_schema", "manufacturing.db")
ISO = eng.ISO

MIN_PLANNING_PARTS = 100

# Demo-scale prune bands (prune_erp_to_demo_scale.already_at_demo_scale): the
# expansion must leave every header count inside its band, or a bootstrap
# re-run would prune the new synthetic supply.
CO_BAND = (10, 20)
WO_BAND = (10, 20)
PO_BAND = (10, 25)

NEW_CO_IDS = ("CO-MRP-001", "CO-MRP-002")
NEW_PO_IDS = ("PO-MRP-BLK1", "PO-MRP-BLK2", "PO-MRP-BLK3")
NEW_WO_COUNT = 5

# --------------------------------------------------------------------------- #
# deterministic part-universe definition (100 parts, mixed classes)
# --------------------------------------------------------------------------- #
_CLASS_PLAN = (
    # (part_class, id_prefix, id_base, count, commodity rotation, uom rotation)
    ("MAKE", "MCH", 51001, 25,
     ("MACHINED-DETAIL", "ASSEMBLY", "COMPOSITE"), ("EA",)),
    ("BUY", "AVN", 52001, 35,
     ("PURCHASED-COMPONENT", "ELECTRICAL", "BEARING", "SEAL"), ("EA",)),
    ("HARDWARE", "HDW", 53001, 20,
     ("HARDWARE",), ("EA",)),
    ("RAW", "RMT", 54001, 15,
     ("RAW-METAL",), ("LB", "FT", "IN")),
    ("OUTSIDE_SERVICE", "OSP", 55001, 5,
     ("OSP-FINISHING", "OSP-THERMAL", "OSP-NDT"), ("EA",)),
)

_NOUNS = {
    "MAKE": ("Machined Rib", "Spar Fitting", "Bulkhead Frame", "Actuator Bracket",
             "Longeron Splice", "Torque Tube", "Gusset Plate", "Hinge Fitting"),
    "BUY": ("Pressure Transducer", "Servo Valve", "Wire Harness", "Duplex Bearing",
            "Fuel Nozzle", "Static Seal", "Relay Module", "Position Sensor"),
    "HARDWARE": ("Hi-Lok Pin", "Blind Rivet", "Self-Locking Nut", "Shear Bolt",
                 "Cotter Pin", "Washer", "Clevis Pin", "Retaining Ring"),
    "RAW": ("Titanium Sheet", "Aluminum Plate", "Stainless Bar", "Inconel Rod",
            "Aluminum Extrusion", "Steel Tube"),
    "OUTSIDE_SERVICE": ("Anodize Detail", "Heat-Treat Lot", "NDT Panel",
                        "Shot-Peen Fitting", "Passivate Manifold"),
}
_QUALIFIERS = ("Wing Station 42", "Fwd Fuselage", "Nacelle Assy", "Aft Pylon",
               "Center Wing Box", "Empennage", "MLG Bay", "Flap Track")
_MATERIAL_SPECS = ("AMS 4911", "6061-T6", "7075-T7351", "AMS 5510",
                   "AMS 5662", "4130 Steel", "2024-T3", "304 SS")


def _crc(*parts) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def build_part_universe():
    """The full deterministic 100-part definition (pure function, no I/O)."""
    parts = []
    for part_class, prefix, base, count, commodities, uoms in _CLASS_PLAN:
        for i in range(count):
            part_id = f"{prefix}-{base + i}"
            noun = _NOUNS[part_class][_crc(part_id, "N") % len(_NOUNS[part_class])]
            qual = _QUALIFIERS[_crc(part_id, "Q") % len(_QUALIFIERS)]
            parts.append({
                "part_id": part_id,
                "part_description": f"{noun}, {qual}",
                "part_class": part_class,
                "unit_of_measure": uoms[_crc(part_id, "U") % len(uoms)],
                "unit_cost": round((_crc(part_id, "C") % 95000) / 100 + 4.5, 2),
                "lead_time_days": _crc(part_id, "L") % 43 + 7,      # 7..49
                "reorder_point": float(_crc(part_id, "R") % 40 + 5),
                "on_hand_qty": float(_crc(part_id, "H") % 226 + 25),  # 25..250
                "revision": "ABC"[_crc(part_id, "V") % 3],
                "cage_code": f"{_crc(part_id, 'G') % 90000 + 10000}",
                "drawing_number": f"DWG-{prefix}-{base + i}",
                "material_spec": (
                    _MATERIAL_SPECS[_crc(part_id, "M") % len(_MATERIAL_SPECS)]
                    if part_class in ("RAW", "MAKE") else None
                ),
                "commodity_code": commodities[_crc(part_id, "K") % len(commodities)],
                "buyer_code": (
                    None if part_class == "MAKE"
                    else f"BUYER-{_crc(part_id, 'B') % 10 + 1}"
                ),
            })
    return parts


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    as_of = eng.compute_as_of(conn)
    plan_start = eng.plan_start(as_of)
    buckets = eng.month_buckets(as_of)

    universe = build_part_universe()

    # 1. Part master (INSERT OR IGNORE on part_id — idempotent). ---------------
    inserted_parts = 0
    for p in universe:
        cur.execute(
            "INSERT OR IGNORE INTO part "
            "(part_id, part_description, part_class, unit_of_measure, unit_cost, "
            " lead_time_days, reorder_point, on_hand_qty, revision, cage_code, "
            " drawing_number, material_spec, planner_code, buyer_code, active, "
            " commodity_code) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (p["part_id"], p["part_description"], p["part_class"],
             p["unit_of_measure"], p["unit_cost"], p["lead_time_days"],
             p["reorder_point"], p["on_hand_qty"], p["revision"], p["cage_code"],
             p["drawing_number"], p["material_spec"], "ENGINEERING",
             p["buyer_code"], p["commodity_code"]),
        )
        inserted_parts += cur.rowcount

    # 2. Open demand: two customer orders, one line per new part. --------------
    co_dates = {
        NEW_CO_IDS[0]: (plan_start - timedelta(days=45)).strftime(ISO),
        NEW_CO_IDS[1]: (plan_start - timedelta(days=30)).strftime(ISO),
    }
    co_customers = {
        NEW_CO_IDS[0]: "Meridian Aerostructures",
        NEW_CO_IDS[1]: "Pacific Turbine Systems",
    }
    for co_id in NEW_CO_IDS:
        cur.execute(
            "INSERT OR IGNORE INTO customer_order "
            "(order_id, customer_name, order_date, site_id, status) "
            "VALUES (?, ?, ?, 'SITE-1', 'Open')",
            (co_id, co_customers[co_id], co_dates[co_id]),
        )

    half = len(universe) // 2
    inserted_lines = 0
    for idx, p in enumerate(universe):
        co_id = NEW_CO_IDS[0] if idx < half else NEW_CO_IDS[1]
        line_no = (idx % half) + 1
        qty = float(_crc(p["part_id"], "DQ") % 56 + 5)  # 5..60
        cur.execute(
            "INSERT INTO customer_order_line "
            "(order_id, line_no, part_id, site_id, order_qty, unit_price) "
            "SELECT ?, ?, ?, 'SITE-1', ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM customer_order_line "
            "                  WHERE order_id=? AND part_id=?)",
            (co_id, line_no, p["part_id"], qty,
             round(p["unit_cost"] * 1.35, 2), co_id, p["part_id"]),
        )
        inserted_lines += cur.rowcount

    # Demand timing — recomputed EVERY run with backfill_mrp_demand_supply's
    # exact formula (crc32("col:<order_line_id>", as_of)) so a backfill re-run
    # lands on identical values (fixed point across both migrations).
    lead = {p["part_id"]: p["lead_time_days"] for p in universe}
    ph = ",".join("?" * len(NEW_CO_IDS))
    demand_updates = []
    for order_line_id, part_id in cur.execute(
        f"SELECT order_line_id, part_id FROM customer_order_line "
        f"WHERE order_id IN ({ph})",
        NEW_CO_IDS,
    ).fetchall():
        need_by = _horizon_date(f"col:{order_line_id}", plan_start, as_of)
        lt = lead.get(part_id)
        rel = need_by - timedelta(days=int(lt)) if lt else None
        demand_updates.append(
            (need_by.strftime(ISO), rel.strftime(ISO) if rel else None, order_line_id)
        )
    cur.executemany(
        "UPDATE customer_order_line SET need_by_date=?, desired_release_date=? "
        "WHERE order_line_id=?",
        demand_updates,
    )

    # 3. Supply: consolidated block POs for all buy-side parts. ----------------
    material_suppliers = [
        r[0] for r in cur.execute(
            "SELECT supplier_id FROM suppliers "
            "WHERE outside_service=0 AND active=1 ORDER BY supplier_id LIMIT 3"
        ).fetchall()
    ]
    if not material_suppliers:
        raise RuntimeError("no active material supplier for block POs (fail closed)")

    buy_side = [p for p in universe
                if p["part_class"] in ("BUY", "HARDWARE", "RAW", "OUTSIDE_SERVICE")]
    for n, po_id in enumerate(NEW_PO_IDS):
        supplier = material_suppliers[n % len(material_suppliers)]
        req = _horizon_date(f"pomrpblk:{po_id}", plan_start, as_of)
        cur.execute(
            "INSERT OR IGNORE INTO purchase_order "
            "(po_id, supplier_id, po_type, po_date, required_date, status, total_cost) "
            "VALUES (?, ?, 'material', ?, ?, 'Open', 0)",
            (po_id, supplier, plan_start.strftime(ISO), req.strftime(ISO)),
        )
    inserted_po_lines = 0
    for idx, p in enumerate(buy_side):
        po_id = NEW_PO_IDS[idx % len(NEW_PO_IDS)]
        qty = float(_crc(p["part_id"], "SQ") % 120 + 20)  # 20..139
        cur.execute(
            "INSERT INTO po_line "
            "(po_id, part_id, part_description, quantity, unit_cost, line_total) "
            "SELECT ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM po_line WHERE po_id=? AND part_id=?)",
            (po_id, p["part_id"], p["part_description"], qty, p["unit_cost"],
             round(qty * p["unit_cost"], 2), po_id, p["part_id"]),
        )
        inserted_po_lines += cur.rowcount
    for po_id in NEW_PO_IDS:  # keep header total in lockstep with lines
        cur.execute(
            "UPDATE purchase_order SET total_cost = "
            "(SELECT ROUND(COALESCE(SUM(line_total), 0), 2) FROM po_line WHERE po_id=?) "
            "WHERE po_id=?",
            (po_id, po_id),
        )

    # 4. Supply: open work orders for the first MAKE parts (in-house WIP). -----
    make_parts = [p for p in universe if p["part_class"] == "MAKE"][:NEW_WO_COUNT]
    wo_statuses = ("released", "firmed", "released", "unreleased", "released")
    inserted_wos = 0
    for n, p in enumerate(make_parts):
        wo_id = f"WO-MRP-{n + 1:03d}"
        req = _horizon_date(f"womrp:{wo_id}", plan_start, as_of)
        cur.execute(
            "INSERT OR IGNORE INTO work_order "
            "(wo_id, workorder_type, part_id, part_description, quantity, status, "
            " open_date, close_date, required_date, routing_template, "
            " outside_service, site_id) "
            "VALUES (?, 'M', ?, ?, ?, ?, ?, NULL, ?, 'MACHINED', 0, 'SITE-1')",
            (wo_id, p["part_id"], p["part_description"],
             float(_crc(p["part_id"], "WQ") % 40 + 10),
             wo_statuses[n % len(wo_statuses)],
             plan_start.strftime(ISO), req.strftime(ISO)),
        )
        inserted_wos += cur.rowcount

    conn.commit()

    # 5. Fail-closed verification. ---------------------------------------------
    n_parts = cur.execute("SELECT COUNT(*) FROM part").fetchone()[0]
    n_new = cur.execute(
        "SELECT COUNT(*) FROM part WHERE part_id IN (%s)"
        % ",".join("?" * len(universe)),
        [p["part_id"] for p in universe],
    ).fetchone()[0]
    counts = {
        t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customer_order", "work_order", "purchase_order")
    }

    summary = eng.validate_planning_inputs(conn)
    planning = eng.list_planning_parts(conn)
    planning_ids = {row["part_id"] for row in planning}

    # A sample grid per class must compute without a fail-closed error.
    sample = {}
    for part_class, prefix, base, _count, _c, _u in _CLASS_PLAN:
        pid = f"{prefix}-{base}"
        grid = eng.compute_mrp_grid(conn, pid)
        sample[pid] = grid["part_class"]

    # Collapse the WAL so the committed main DB file reflects these writes.
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.commit()
    conn.close()

    print(f"  as-of date (data-derived): {as_of.strftime(ISO)}")
    print(f"  horizon: {buckets[0][0]} .. {buckets[-1][0]}")
    print(f"  new parts inserted this run:      {inserted_parts} (universe {len(universe)})")
    print(f"  new CO lines inserted this run:   {inserted_lines}")
    print(f"  new PO lines inserted this run:   {inserted_po_lines}")
    print(f"  new WOs inserted this run:        {inserted_wos}")
    print(f"  part master total:                {n_parts}")
    print(f"  header counts: CO={counts['customer_order']} "
          f"WO={counts['work_order']} PO={counts['purchase_order']}")
    print(f"  planning parts in horizon:        {len(planning)} "
          f"(validation: {summary['demand_parts']})")
    print(f"  sample grids computed: {', '.join(f'{k} ({v})' for k, v in sample.items())}")

    assert n_new == len(universe), (
        f"expected all {len(universe)} expansion parts in master, found {n_new}"
    )
    assert len(planning) >= MIN_PLANNING_PARTS, (
        f"MRP dropdown must list >= {MIN_PLANNING_PARTS} parts, got {len(planning)}"
    )
    missing = [p["part_id"] for p in universe if p["part_id"] not in planning_ids]
    assert not missing, f"expansion parts missing open in-horizon demand: {missing[:5]}"
    for (table, count), (lo, hi) in zip(counts.items(),
                                        (CO_BAND, WO_BAND, PO_BAND)):
        assert lo <= count <= hi, (
            f"{table} count {count} left the demo-scale band [{lo}, {hi}] — "
            "prune_erp_to_demo_scale would trim the MRP expansion on re-run"
        )
    print("Done. MRP part universe expanded; fail-closed validation passed.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
