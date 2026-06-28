"""
Migration: Backfill supplier performance ratings and work-order actual costs
from the real purchasing -> receiving -> payables flow (never random numbers).

The synthetic ERP shipped with two empty columns that made dashboards read as
blank/zero:
  - suppliers.performance_rating was NULL for most suppliers.
  - work_order.act_lab_cost / act_bur_cost / act_ser_cost / act_mat_cost were all
    0.0 for every work order.

Rather than invent values, this migration DERIVES them from data that already
exists and is internally coherent (the canonical SQL-Server flow these tables
mirror is documented in Data_Models/Payables/: PURCHASE_ORDER -> PURC_ORDER_LINE
-> RECEIVER_LINE (received qty) -> PAYABLE_LINE -> PAYABLE).

--------------------------------------------------------------------------------
SUPPLY PERSPECTIVE — suppliers.performance_rating
--------------------------------------------------------------------------------
A supplier's score is a function of how it actually performed in the receiving
data, exactly as a real supplier scorecard works:
  - On-time delivery (OTD): fraction of that supplier's receipts whose
    receipt_date <= the purchase order's required_date (the DESIRED_RECV_DATE in
    the canonical model). Receipts on POs with no required_date are ignored.
  - Quality acceptance: (Passed + Waived) / (Passed + Waived + Failed) from
    receiving.inspection_status. 'Pending' rows are not yet graded, so excluded.
    A supplier with no graded receipts gets a neutral 0.75.
  rating = clamp(5.0 * (0.55*OTD + 0.45*quality), 1.0, 5.0), rounded to 2dp.
A supplier with no receipts at all (no track record) is left at a neutral 3.0
rather than penalized.
ALL suppliers are (re)computed so the column is one consistent, explainable
function of the supply flow (the few pre-seeded random ratings are replaced).

--------------------------------------------------------------------------------
WORK-ORDER ACTUAL COSTS (job costing — internal labor + external procurement)
--------------------------------------------------------------------------------
Per work order the four actual-cost buckets are assembled from their real source:
  - act_lab_cost / act_bur_cost (INTERNAL): the operation routing's estimated
    labor/burden, recognized in step with real operation progress —
    status 'C' (Complete) counts 100%, 'S' (Started) 50%, 'Q' (Queued) 0%.
    A small per-work-order variance (actual jobs run a little over/under
    estimate) is applied to the recognized amount, deterministically seeded by
    crc32(wo_id) so re-runs reproduce the same numbers. Not-started work
    (unreleased / firmed -> all ops 'Q') therefore accrues 0 internal cost,
    matching migrations/backfill_operation_progress.py.
  - act_ser_cost (EXTERNAL outside service): sum of this work order's
    outside_service purchase orders that have actually been RECEIVED
    (purchasing -> receiving). Cost is recognized at receipt, not at PO placement.
  - act_mat_cost (EXTERNAL material): sum of material_issue.total_cost issued to
    the work order (material purchased -> received -> issued to the floor).

Idempotency: every value is a pure function of existing rows (+ crc32-seeded
variance), so the migration is a fixed point — safe to re-run, identical result.
Costs are written with UPDATE by primary key (suppliers.supplier_id /
work_order.wo_id). The certified ArangoDB graph is never touched.
"""
import argparse
import os
import sqlite3
import zlib
from random import Random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# Operation-status -> fraction of its estimated cost recognized as "actual".
STATUS_WEIGHT = {"C": 1.0, "S": 0.5, "Q": 0.0}

# Supplier scorecard weights (must sum to 1.0): on-time delivery vs. quality.
W_OTD = 0.55
W_QUALITY = 0.45
NEUTRAL_QUALITY = 0.75  # supplier with no graded (Passed/Failed/Waived) receipts
NO_HISTORY_RATING = 3.0  # supplier with no receipts at all -> neutral, not penalized


def rng_for(key: str) -> Random:
    """Deterministic RNG seeded by a stable crc32 of the key (process-independent)."""
    return Random(zlib.crc32(key.encode()))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def backfill_supplier_ratings(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT s.supplier_id,
               AVG(CASE WHEN po.required_date IS NOT NULL
                        THEN (CASE WHEN r.receipt_date <= po.required_date
                                   THEN 1.0 ELSE 0.0 END)
                   END)                                              AS otd,
               SUM(CASE WHEN r.inspection_status IN ('Passed','Waived')
                        THEN 1 ELSE 0 END)                          AS good,
               SUM(CASE WHEN r.inspection_status = 'Failed'
                        THEN 1 ELSE 0 END)                          AS bad,
               COUNT(r.supplier_id)                                 AS recs
        FROM suppliers s
        LEFT JOIN receiving r       ON r.supplier_id = s.supplier_id
        LEFT JOIN purchase_order po ON r.po_id = po.po_id
        GROUP BY s.supplier_id
        """
    ).fetchall()

    updated = 0
    for supplier_id, otd, good, bad, recs in rows:
        if not recs:  # no receipts at all -> neutral, no track record to score
            rating = NO_HISTORY_RATING
        else:
            otd = otd if otd is not None else 0.0
            graded = (good or 0) + (bad or 0)
            quality = (good / graded) if graded else NEUTRAL_QUALITY
            rating = round(clamp(5.0 * (W_OTD * otd + W_QUALITY * quality), 1.0, 5.0), 2)
        conn.execute(
            "UPDATE suppliers SET performance_rating = ? WHERE supplier_id = ?",
            (rating, supplier_id),
        )
        updated += 1
    return updated


def _rollup(conn: sqlite3.Connection, sql: str):
    return {row[0]: row for row in conn.execute(sql).fetchall()}


def backfill_wo_actuals(conn: sqlite3.Connection) -> int:
    # Internal labor/burden recognized in step with operation progress (C/S/Q).
    labor = _rollup(
        conn,
        """
        SELECT wo_id,
               SUM(est_atl_lab_cost * CASE status WHEN 'C' THEN 1.0
                                                  WHEN 'S' THEN 0.5
                                                  ELSE 0.0 END) AS lab,
               SUM(est_atl_bur_cost * CASE status WHEN 'C' THEN 1.0
                                                  WHEN 'S' THEN 0.5
                                                  ELSE 0.0 END) AS bur
        FROM operation
        GROUP BY wo_id
        """,
    )
    # External outside service: only POs that have actually been received.
    service = _rollup(
        conn,
        """
        SELECT po.wo_id, SUM(po.total_cost) AS ser
        FROM purchase_order po
        WHERE po.po_type = 'outside_service'
          AND po.wo_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM receiving r WHERE r.po_id = po.po_id)
        GROUP BY po.wo_id
        """,
    )
    # External material: what was actually issued to the work order.
    material = _rollup(
        conn,
        "SELECT wo_id, SUM(total_cost) AS mat FROM material_issue GROUP BY wo_id",
    )

    wo_ids = [r[0] for r in conn.execute("SELECT wo_id FROM work_order").fetchall()]
    updated = 0
    for wo_id in wo_ids:
        lab_est = (labor.get(wo_id) or (None, 0.0, 0.0))[1] or 0.0
        bur_est = (labor.get(wo_id) or (None, 0.0, 0.0))[2] or 0.0
        # actual-vs-estimate variance on the recognized (completed) portion only.
        variance = 0.92 + rng_for(wo_id).random() * 0.20  # 0.92 .. 1.12
        act_lab = round(lab_est * variance, 2)
        act_bur = round(bur_est * variance, 2)
        act_ser = round((service.get(wo_id) or (None, 0.0))[1] or 0.0, 2)
        act_mat = round((material.get(wo_id) or (None, 0.0))[1] or 0.0, 2)
        conn.execute(
            "UPDATE work_order SET act_lab_cost = ?, act_bur_cost = ?, "
            "act_ser_cost = ?, act_mat_cost = ? WHERE wo_id = ?",
            (act_lab, act_bur, act_ser, act_mat, wo_id),
        )
        updated += 1
    return updated


def verify(conn: sqlite3.Connection) -> None:
    s_total, s_rated = conn.execute(
        "SELECT COUNT(*), COUNT(performance_rating) FROM suppliers"
    ).fetchone()
    s_min, s_max, s_avg = conn.execute(
        "SELECT ROUND(MIN(performance_rating),2), ROUND(MAX(performance_rating),2), "
        "ROUND(AVG(performance_rating),2) FROM suppliers"
    ).fetchone()
    print(f"  suppliers: {s_rated}/{s_total} rated  (min {s_min}, avg {s_avg}, max {s_max})")

    wo_total, wo_costed = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN act_lab_cost+act_bur_cost+act_ser_cost+act_mat_cost > 0 "
        "THEN 1 ELSE 0 END) FROM work_order"
    ).fetchone()
    print(f"  work_order: {wo_costed}/{wo_total} have non-zero actual cost")
    print("  actual cost by status (lab / bur / ser / mat):")
    for status, n, lab, bur, ser, mat in conn.execute(
        "SELECT status, COUNT(*), ROUND(SUM(act_lab_cost),0), ROUND(SUM(act_bur_cost),0), "
        "ROUND(SUM(act_ser_cost),0), ROUND(SUM(act_mat_cost),0) "
        "FROM work_order GROUP BY status ORDER BY status"
    ).fetchall():
        print(f"    {status:<11} n={n:<4} {lab:>12,.0f} {bur:>12,.0f} {ser:>10,.0f} {mat:>12,.0f}")

    # Provenance checks: the external buckets must tie to their source tables.
    src_ser = conn.execute(
        "SELECT ROUND(SUM(po.total_cost),2) FROM purchase_order po "
        "WHERE po.po_type='outside_service' AND po.wo_id IS NOT NULL "
        "AND EXISTS (SELECT 1 FROM receiving r WHERE r.po_id=po.po_id) "
        "AND po.wo_id IN (SELECT wo_id FROM work_order)"
    ).fetchone()[0] or 0.0
    wo_ser = conn.execute("SELECT ROUND(SUM(act_ser_cost),2) FROM work_order").fetchone()[0] or 0.0
    src_mat = conn.execute(
        "SELECT ROUND(SUM(total_cost),2) FROM material_issue "
        "WHERE wo_id IN (SELECT wo_id FROM work_order)"
    ).fetchone()[0] or 0.0
    wo_mat = conn.execute("SELECT ROUND(SUM(act_mat_cost),2) FROM work_order").fetchone()[0] or 0.0
    print(f"  ties out: outside-service WO={wo_ser:,.2f} vs received-PO source={src_ser:,.2f} "
          f"-> {'OK' if abs(wo_ser-src_ser) < 1.0 else 'MISMATCH'}")
    print(f"  ties out: material WO={wo_mat:,.2f} vs material_issue source={src_mat:,.2f} "
          f"-> {'OK' if abs(wo_mat-src_mat) < 1.0 else 'MISMATCH'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_PATH, help="Path to manufacturing.db")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        print(f"Backfilling supplier ratings + work-order actuals in {args.db}")
        n_sup = backfill_supplier_ratings(conn)
        n_wo = backfill_wo_actuals(conn)
        conn.commit()
        print(f"  updated {n_sup} suppliers, {n_wo} work orders")
        print("Verification:")
        verify(conn)
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
