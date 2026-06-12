"""
Migration: Make operation routing sequences realistic and seed operation-level
MATERIAL requirements.

Two parts, both additive and safe to re-run:

  PART A — Realistic gapped sequence numbers
  ------------------------------------------
  Real ERP routings number their steps with gaps so new operations can be
  inserted later (10, 20, 40, 80, 220 …) rather than the perfectly even
  10/20/30/40 the synthetic seeders emit. This re-numbers operation.sequence_no
  for every work order into a deterministic, strictly-increasing GAPPED sequence
  and keeps labor_ticket.sequence_no (documented to "match operation.sequence_no")
  aligned in lockstep.

  PART B — Operation-level MATERIAL requirements
  ----------------------------------------------
  Materials only used to hang off the whole work order (material_issue.wo_id).
  This seeds the EXISTING, purpose-built `requirement` table (requirement_type
  'MATERIAL') so each requirement is tied to a SPECIFIC operation via
  operation_rowid (-> operation.rowid_pk) and material_part_id (-> part). Now you
  can ask "what material does operation X need?". Only some operations need
  material ("may have"): the first machining/fabrication op of each work order
  consumes RAW stock, and each assembly op consumes a HARDWARE component.

Why this is a migration (not a generator change):
  The committed app_schema/manufacturing.db is the shipping artifact and already
  holds operations from BOTH seeders (scripts/seed_erp_synthetic.py and
  migrations/add_purchasing_wip_tables.py). This migration reads the live
  operation table, so it covers every row regardless of which seeder made it. The
  seeders themselves keep emitting plain multiples-of-10 and carry a docstring
  note pointing here (same pattern as migrations/add_operation_type.py).

Idempotency (safe to re-run — it is a fixed point):
  - The gapped value for each op is a pure function of (wo_id, ordinal position)
    using a crc32(wo_id)-seeded RNG. zlib.crc32 is used on purpose — Python's
    builtin hash() is salted per process (PYTHONHASHSEED) and would NOT be stable
    across runs. Because the new value depends on ordinal (stable under any
    order-preserving renumber), re-running re-derives the identical sequence, so a
    second run changes nothing.
  - The UNIQUE(wo_id, sequence_no) constraint is dodged with a two-pass update:
    shift every sequence_no out of range (+1,000,000) then set the final values
    by primary key.
  - labor_ticket is updated by ticket_id (its PK) using the
    (wo_id, old_seq) -> new_seq map, never by matching live values.
  - requirement rows use deterministic ids (REQ-<wo_id>-<seq>) inserted with
    INSERT OR IGNORE.

CAVEAT: requirement ids are keyed on the final gapped seq. This DB is a frozen
synthetic dataset, so that is safe to re-run. But if a work order's operation rows
are ever ADDED or REMOVED and this is re-run, the gapped values shift and
INSERT OR IGNORE would add NEW requirement rows while the stale ones remain. In
that case re-derive the MATERIAL rows (DELETE them first) — operation_rowid stays
valid, only the seq value moves.

Run once (safe to re-run):
    cd hf-space-inventory-sqlgen
    python migrations/regap_and_seed_requirements.py
"""

import os
import sqlite3
import zlib
from random import Random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# ── Sequence re-gap design ────────────────────────────────────────────────────
START_CHOICES = [10, 20, 30]            # first routing step
GAP_CHOICES   = [20, 40, 60, 80, 120]   # gap added before each later step
SHIFT         = 1_000_000               # temporary offset to dodge the UNIQUE index

# ── Material-requirement design ───────────────────────────────────────────────
# The first op of one of these kinds, per work order, consumes RAW stock.
MACHINING_FIRST_TYPES = {"CNC", "TURN", "WELD", "WJET"}
# Every assembly op consumes a HARDWARE component (fasteners, fittings, …).
HARDWARE_OP_TYPE = "ASSY"


def _rng(key: str) -> Random:
    """Deterministic RNG seeded by a stable crc32 of the key (process-independent)."""
    return Random(zlib.crc32(key.encode()))


def gapped_sequence(wo_id: str, n: int):
    """A deterministic, strictly-increasing GAPPED routing sequence of length n.

    Pure function of (wo_id, ordinal), so applying it to an already-gapped work
    order reproduces the same values — the re-gap is a fixed point."""
    rng = _rng(wo_id)
    out, cur = [], rng.choice(START_CHOICES)
    for i in range(n):
        if i:
            cur += rng.choice(GAP_CHOICES)
        out.append(cur)
    return out


def regap_sequences(cur):
    """PART A: renumber operation.sequence_no into gapped values and keep
    labor_ticket.sequence_no aligned. Returns (n_ops, orphan_labor_tickets)."""
    ops = cur.execute(
        "SELECT rowid_pk, wo_id, sequence_no FROM operation "
        "ORDER BY wo_id, sequence_no"
    ).fetchall()

    by_wo = {}
    for rowid_pk, wo_id, seq in ops:
        by_wo.setdefault(wo_id, []).append((rowid_pk, seq))

    rowid_to_new = {}                 # rowid_pk -> new sequence_no
    oldkey_to_new = {}                # (wo_id, old_seq) -> new_seq  (for labor_ticket)
    for wo_id, lst in by_wo.items():  # lst is already ordered by current seq
        new_seqs = gapped_sequence(wo_id, len(lst))
        for (rowid_pk, old_seq), new_seq in zip(lst, new_seqs):
            rowid_to_new[rowid_pk] = new_seq
            oldkey_to_new[(wo_id, old_seq)] = new_seq

    # labor_ticket map is built from the CURRENT (pre-shift) operation values; read
    # the tickets before we touch anything (the shift only changes operation).
    tickets = cur.execute(
        "SELECT ticket_id, wo_id, sequence_no FROM labor_ticket"
    ).fetchall()

    # Two-pass operation update to avoid UNIQUE(wo_id, sequence_no) collisions.
    cur.execute(f"UPDATE operation SET sequence_no = sequence_no + {SHIFT}")
    cur.executemany(
        "UPDATE operation SET sequence_no=? WHERE rowid_pk=?",
        [(new_seq, rowid_pk) for rowid_pk, new_seq in rowid_to_new.items()],
    )

    # Re-point labor tickets by ticket_id (their PK), never by live value match.
    lt_updates, orphans = [], []
    for ticket_id, wo_id, seq in tickets:
        new = oldkey_to_new.get((wo_id, seq))
        if new is None:
            orphans.append((ticket_id, wo_id, seq))
        else:
            lt_updates.append((new, ticket_id))
    if lt_updates:
        cur.executemany(
            "UPDATE labor_ticket SET sequence_no=? WHERE ticket_id=?", lt_updates
        )

    return len(ops), orphans


def seed_material_requirements(cur):
    """PART B: seed MATERIAL rows into the existing `requirement` table, linked to
    concrete operations. Returns the number of requirement rows after seeding."""
    raw_parts = cur.execute(
        "SELECT part_id, unit_cost FROM part "
        "WHERE part_class='RAW' AND active=1 ORDER BY part_id"
    ).fetchall()
    hardware_parts = cur.execute(
        "SELECT part_id, unit_cost FROM part "
        "WHERE part_class='HARDWARE' AND active=1 ORDER BY part_id"
    ).fetchall()
    if not raw_parts or not hardware_parts:
        raise RuntimeError("part catalog missing RAW or HARDWARE parts — cannot seed requirements")

    ops = cur.execute(
        "SELECT rowid_pk, wo_id, sequence_no, operation_type_id FROM operation "
        "ORDER BY wo_id, sequence_no"
    ).fetchall()

    by_wo = {}
    for rowid_pk, wo_id, seq, otype in ops:
        by_wo.setdefault(wo_id, []).append((rowid_pk, seq, otype))

    wo_qty = {r[0]: (r[1] or 1.0) for r in
              cur.execute("SELECT wo_id, quantity FROM work_order")}

    rows = []
    for wo_id, lst in by_wo.items():
        qty_units = max(float(wo_qty.get(wo_id, 1.0)), 1.0)

        # (1) first machining/fab op of the work order -> RAW stock requirement
        first_mach = next(
            ((rid, seq) for rid, seq, ot in lst if ot in MACHINING_FIRST_TYPES),
            None,
        )
        if first_mach:
            rid, seq = first_mach
            rng = _rng(f"RAW:{wo_id}")
            part_id, unit_cost = rng.choice(raw_parts)
            std = round(rng.uniform(1.0, 4.0), 2)
            actual = round(std * qty_units, 2)
            rows.append((
                f"REQ-{wo_id}-{seq}", "WORK_ORDER", wo_id, "WORK_ORDER", "MATERIAL",
                seq, rid, part_id, std, actual, unit_cost, round(actual * unit_cost, 2),
            ))

        # (2) each assembly op -> HARDWARE component requirement
        for rid, seq, ot in lst:
            if ot == HARDWARE_OP_TYPE:
                rng = _rng(f"HW:{wo_id}:{seq}")
                part_id, unit_cost = rng.choice(hardware_parts)
                std = float(rng.randint(4, 24))
                actual = round(std * qty_units, 2)
                rows.append((
                    f"REQ-{wo_id}-{seq}", "WORK_ORDER", wo_id, "WORK_ORDER", "MATERIAL",
                    seq, rid, part_id, std, actual, unit_cost, round(actual * unit_cost, 2),
                ))

    if rows:
        cur.executemany(
            "INSERT OR IGNORE INTO requirement "
            "(requirement_id, component_type, component_id, requirement_level, "
            "requirement_type, operation_seq, operation_rowid, material_part_id, "
            "std_qty, actual_qty, unit_cost, extended_cost) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )

    return cur.execute(
        "SELECT COUNT(*) FROM requirement WHERE requirement_type='MATERIAL'"
    ).fetchone()[0]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # PART A — re-gap routing sequences --------------------------------------
    n_ops, orphans = regap_sequences(cur)
    print(f"  operation: {n_ops} rows re-numbered into gapped sequences")
    if orphans:
        print(f"  WARNING — {len(orphans)} labor_ticket row(s) had no matching "
              f"operation and were left unchanged:")
        for ticket_id, wo_id, seq in orphans[:20]:
            print(f"    ticket_id={ticket_id} wo_id={wo_id} sequence_no={seq}")
    else:
        print("  labor_ticket: re-aligned, 0 orphans")

    # PART B — seed operation-level MATERIAL requirements --------------------
    total_material = seed_material_requirements(cur)
    print(f"  requirement: {total_material} MATERIAL rows tied to operations")

    conn.commit()

    # Quick sanity report.
    print("  sample gapped sequences (one work order):")
    sample_wo = cur.execute(
        "SELECT wo_id FROM operation ORDER BY wo_id LIMIT 1"
    ).fetchone()
    if sample_wo:
        seqs = [r[0] for r in cur.execute(
            "SELECT sequence_no FROM operation WHERE wo_id=? ORDER BY sequence_no",
            (sample_wo[0],),
        )]
        print(f"    {sample_wo[0]}: {seqs}")
    print("  requirement by material part (top 5):")
    for part_id, n in cur.execute(
        "SELECT material_part_id, COUNT(*) FROM requirement "
        "WHERE requirement_type='MATERIAL' GROUP BY material_part_id "
        "ORDER BY COUNT(*) DESC LIMIT 5"
    ):
        print(f"    {part_id:<10} {n}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
