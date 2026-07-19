"""Seed a fabricated angle-bracket DETAIL part + its design-level BOM usage.

What (synthetic design data, SQLite target):
  1. Part BRKT-70001 "Angle Bracket, Machined Detail" — a MAKE-class
     fabricated detail (own drawing, 6061-T6, fabricated from raw
     extrusion P-10015).
  2. Its OWN design-level material requirement (the fabrication input):
     BRKT-70001 consumes P-10015 (Aluminum Extrusion 6061-T6 2x2).
  3. Design-level BOM rows placing the bracket on SEVERAL parent parts,
     including MCH-51006 (Spar Fitting, Center Wing Box) which is
     scheduled on Friday 2026-07-31 (WO-JUL-31 required/close date and
     the CO-JUL-01 demand line need-by):
       MCH-51006  qty 4   (scheduled Fri 2026-07-31)
       MCH-51011  qty 4   (Spar Fitting sister part)
       MCH-51019  qty 2   (Spar Fitting sister part)
       MCH-51008  qty 2   (Actuator Bracket, MLG Bay)
       MCH-51001  qty 6   (Longeron Splice, Fwd Fuselage)

Requirement rows are DESIGN-level (component_type='PART',
operation_rowid NULL) so they are as-designed standards, not
work-order actuals — existing WO-level requirement data is untouched.

Deterministic, idempotent (INSERT OR IGNORE on natural keys +
unconditional deterministic UPDATEs), fail-closed validation.

Run:
    cd hf-space-inventory-sqlgen && python migrations/seed_angle_bracket_design.py
"""
from __future__ import annotations

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

BRACKET = dict(
    part_id="BRKT-70001",
    part_description="Angle Bracket, Machined Detail",
    part_class="MAKE",
    unit_of_measure="EA",
    unit_cost=24.85,
    lead_time_days=12,
    reorder_point=10.0,
    on_hand_qty=16.0,
    revision="B",
    cage_code="1CQD7",
    drawing_number="DWG-BRKT-70001",
    material_spec="6061-T6",
    planner_code="ENGINEERING",
    commodity_code="MACHINED-DETAIL",
)

RAW_INPUT_PART = "P-10015"          # Aluminum Extrusion 6061-T6 2x2
RAW_STD_QTY = 0.42                  # ft of extrusion per bracket

# (parent part_id, std qty per unit, design operation seq on the parent)
PARENT_USAGE = [
    ("MCH-51006", 4.0, 20),  # Spar Fitting, Center Wing Box — sched Fri 2026-07-31
    ("MCH-51011", 4.0, 20),
    ("MCH-51019", 2.0, 20),
    ("MCH-51008", 2.0, 30),
    ("MCH-51001", 6.0, 40),
]


def run() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    try:
        _seed(cur)
        _validate(cur)
        conn.commit()
        print("Seeded BRKT-70001 angle bracket detail + design BOM on "
              f"{len(PARENT_USAGE)} parent parts (incl. MCH-51006, scheduled 2026-07-31).")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _seed(cur: sqlite3.Cursor) -> None:
    # fail closed if any referenced part is missing
    for pid in [RAW_INPUT_PART] + [p for p, _q, _s in PARENT_USAGE]:
        if not cur.execute("SELECT 1 FROM part WHERE part_id=?", (pid,)).fetchone():
            raise RuntimeError(f"FAIL-CLOSED: referenced part {pid} missing")

    cols = ", ".join(BRACKET)
    ph = ", ".join("?" * len(BRACKET))
    cur.execute(f"INSERT OR IGNORE INTO part ({cols}) VALUES ({ph})",
                tuple(BRACKET.values()))
    # deterministic heal of the descriptive fields (idempotent re-run)
    cur.execute(
        "UPDATE part SET part_description=?, part_class=?, unit_cost=?, "
        "lead_time_days=?, revision=?, drawing_number=?, material_spec=? "
        "WHERE part_id=?",
        (BRACKET["part_description"], BRACKET["part_class"], BRACKET["unit_cost"],
         BRACKET["lead_time_days"], BRACKET["revision"], BRACKET["drawing_number"],
         BRACKET["material_spec"], BRACKET["part_id"]),
    )

    def upsert_design_material(req_id, parent, seq, material, qty, unit_cost):
        ext = round(qty * unit_cost, 2)
        cur.execute(
            "INSERT OR IGNORE INTO requirement (requirement_id, component_type, "
            "component_id, requirement_level, requirement_type, operation_seq, "
            "operation_rowid, material_part_id, std_qty, actual_qty, unit_cost, "
            "extended_cost) VALUES (?, 'PART', ?, 'DESIGN', 'MATERIAL', ?, NULL, "
            "?, ?, 0.0, ?, ?)",
            (req_id, parent, seq, material, qty, unit_cost, ext),
        )
        cur.execute(
            "UPDATE requirement SET std_qty=?, unit_cost=?, extended_cost=? "
            "WHERE requirement_id=?",
            (qty, unit_cost, ext, req_id),
        )

    # the bracket's own fabrication input (raw extrusion)
    raw_cost = cur.execute(
        "SELECT unit_cost FROM part WHERE part_id=?", (RAW_INPUT_PART,)
    ).fetchone()[0]
    upsert_design_material(
        f"REQ-DSN-{BRACKET['part_id']}-10", BRACKET["part_id"], 10,
        RAW_INPUT_PART, RAW_STD_QTY, raw_cost,
    )

    # where-used: the bracket as a design BOM component of each parent
    for parent, qty, seq in PARENT_USAGE:
        upsert_design_material(
            f"REQ-DSN-{parent}-{seq}-BRKT", parent, seq,
            BRACKET["part_id"], qty, BRACKET["unit_cost"],
        )


def _validate(cur: sqlite3.Cursor) -> None:
    failures = []

    n = cur.execute(
        "SELECT COUNT(*) FROM requirement WHERE requirement_level='DESIGN' "
        "AND material_part_id=?", (BRACKET["part_id"],)
    ).fetchone()[0]
    if n != len(PARENT_USAGE):
        failures.append(f"expected {len(PARENT_USAGE)} where-used rows, found {n}")

    n = cur.execute(
        "SELECT COUNT(*) FROM requirement WHERE requirement_level='DESIGN' "
        "AND component_id=? AND material_part_id=?",
        (BRACKET["part_id"], RAW_INPUT_PART),
    ).fetchone()[0]
    if n != 1:
        failures.append(f"expected 1 fabrication-input row, found {n}")

    # at least one parent must be scheduled on Friday 2026-07-31
    n = cur.execute(
        "SELECT COUNT(*) FROM requirement r JOIN work_order w "
        "ON w.part_id = r.component_id "
        "WHERE r.requirement_level='DESIGN' AND r.material_part_id=? "
        "AND date(w.required_date)='2026-07-31'",
        (BRACKET["part_id"],),
    ).fetchone()[0]
    if n < 1:
        failures.append("no parent of the bracket is scheduled on 2026-07-31")

    # cent-exact extended costs
    for req_id, q, uc, ext in cur.execute(
        "SELECT requirement_id, std_qty, unit_cost, extended_cost FROM requirement "
        "WHERE requirement_id LIKE 'REQ-DSN-%'"
    ).fetchall():
        if round(q * uc, 2) != round(ext, 2):
            failures.append(f"{req_id}: extended_cost {ext} != qty*cost")

    if failures:
        raise RuntimeError("FAIL-CLOSED: " + "; ".join(failures))


if __name__ == "__main__":
    run()
