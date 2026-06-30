"""
Migration: Backfill operation-level actual cost accrual and reconcile it to the
work-order rollups.

The synthetic ERP set the four work_order.act_* rollups (see
migrations/backfill_supplier_rating_and_wo_actuals.py) but left the OPERATION-level
actuals (operation.act_atl_lab_cost / act_atl_bur_cost / act_atl_ser_cost) all
0.0 — so a job's cost could not be read step-by-step, and the operation actuals did
not roll up to the work order.

This migration DERIVES per-operation actuals from data that already exists and is
internally coherent, never random, and reconciles them EXACTLY to the work-order
rollups (the rollups are the source of truth):

INTERNAL LABOR / BURDEN (act_atl_lab_cost / act_atl_bur_cost)
  work_order.act_lab_cost / act_bur_cost were built as
      SUM(operation.est_atl_* * STATUS_WEIGHT[status]) * per-WO variance,
  so the work-order total is exactly the sum of each progressed step's recognized
  estimate scaled by one WO-level variance. We therefore distribute the rollup
  back DOWN to the progressed in-house operations (service_id IS NULL, status C/S)
  in proportion to that same recognized-estimate shape
  (est_atl_* * STATUS_WEIGHT[status]). The per-WO rounding residual is placed on
  the last progressed step so the operation actuals sum to the rollup to the cent.
  Queued steps (and outside-service steps) accrue 0 internal labor/burden.

  Note on labor_ticket: a labor_ticket exists per (wo_id, sequence_no) for some
  steps, but its labor_cost was seeded as hours*rate WITHOUT the build quantity,
  so ticket dollars are systematically a small fraction of the quantity-scaled
  estimate the rollup is built from and cover only ~half of the progressed steps.
  Tickets therefore identify the grain that ran, but the recognized-estimate shape
  (which the rollup is literally the sum of) is the dollar basis that reconciles.

EXTERNAL OUTSIDE SERVICE (act_atl_ser_cost)
  work_order.act_ser_cost is the sum of the WO's outside-service purchase orders
  that have actually been RECEIVED (cost recognized at receipt). Each such PO ties
  to exactly one operation by (wo_id, service_id) — a reliable key (the PO-id seq
  suffix is stale because sequence_no was re-gapped after the POs were created).
  We sum each received outside-service PO's total_cost onto its operation, so the
  operation outside-service actuals sum to the rollup exactly. The PO receipt — not
  the operation's Q/S/C status — is the accrual signal for outside work, so a step
  whose service PO is received accrues even if its status is still Queued.

Idempotency: every value is a pure function of existing rows (work_order rollups,
operation estimates/status, received outside-service POs). Re-running reproduces
the identical state. Every operation's three actual buckets are (re)written, so
the migration is a fixed point. Updates are by operation.rowid_pk. The certified
ArangoDB graph is never touched.

Run order: AFTER migrations/backfill_supplier_rating_and_wo_actuals.py (the
work-order rollups it reconciles to must already be set) and after
migrations/backfill_operation_progress.py (operation status drives recognition).
Safe to re-run.
    cd hf-space-inventory-sqlgen
    python migrations/backfill_operation_actuals.py
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

# Operation-status -> fraction of its estimated cost recognized as "actual".
# Identical to migrations/backfill_supplier_rating_and_wo_actuals.py so the
# operation distribution shape matches how the work-order rollup was assembled.
STATUS_WEIGHT = {"C": 1.0, "S": 0.5, "Q": 0.0}


def _distribute(target: float, ops):
    """Allocate ``target`` dollars across operations by their recognized-estimate
    shape, returning {rowid_pk: amount} that sums to ``target`` to the cent.

    ``ops`` is a list of (rowid_pk, sequence_no, shape_weight). Only operations
    with shape_weight > 0 are eligible (a Queued step has weight 0). The rounding
    residual lands on the last eligible step (by sequence_no) so the per-WO sum is
    exact. Returns 0.0 for every op when target<=0 or nothing is eligible.
    """
    out = {rowid_pk: 0.0 for rowid_pk, _, _ in ops}
    if target <= 0:
        return out
    eligible = [(rowid_pk, seq, w) for rowid_pk, seq, w in ops if w > 0]
    if not eligible:
        return out
    total_w = sum(w for _, _, w in eligible)
    if total_w > 0:
        for rowid_pk, _, w in eligible:
            out[rowid_pk] = round(target * w / total_w, 2)
    else:  # all eligible have zero shape -> equal split among them
        share = round(target / len(eligible), 2)
        for rowid_pk, _, _ in eligible:
            out[rowid_pk] = share
    # Place the rounding residual on the last eligible step (by sequence_no).
    residual = round(target - sum(out.values()), 2)
    if residual:
        last_rowid = sorted(eligible, key=lambda e: e[1])[-1][0]
        out[last_rowid] = round(out[last_rowid] + residual, 2)
    return out


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    wo_rollups = {
        r[0]: (r[1] or 0.0, r[2] or 0.0)
        for r in cur.execute(
            "SELECT wo_id, act_lab_cost, act_bur_cost FROM work_order"
        )
    }

    # Received outside-service PO cost per (wo_id, service_id) — the outside-service
    # accrual recognized at receipt, tied to the operation by (wo_id, service_id).
    ser_by_op = {}
    for wo_id, service_id, cost in cur.execute(
        """
        SELECT po.wo_id, po.service_id, SUM(po.total_cost)
        FROM purchase_order po
        WHERE po.po_type = 'outside_service'
          AND po.wo_id IS NOT NULL
          AND po.service_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM receiving r WHERE r.po_id = po.po_id)
        GROUP BY po.wo_id, po.service_id
        """
    ):
        ser_by_op[(wo_id, service_id)] = cost or 0.0

    by_wo = {}
    for rowid_pk, wo_id, seq, service_id, est_lab, est_bur, status in cur.execute(
        "SELECT rowid_pk, wo_id, sequence_no, service_id, "
        "est_atl_lab_cost, est_atl_bur_cost, status FROM operation "
        "ORDER BY wo_id, sequence_no"
    ):
        by_wo.setdefault(wo_id, []).append(
            (rowid_pk, seq, service_id, est_lab or 0.0, est_bur or 0.0, status)
        )

    updates = []  # (act_lab, act_bur, act_ser, rowid_pk)
    for wo_id, ops in by_wo.items():
        target_lab, target_bur = wo_rollups.get(wo_id, (0.0, 0.0))
        inhouse = [
            (rowid_pk, seq, est_lab * STATUS_WEIGHT.get(status, 0.0))
            for rowid_pk, seq, service_id, est_lab, est_bur, status in ops
            if service_id is None
        ]
        inhouse_bur = [
            (rowid_pk, seq, est_bur * STATUS_WEIGHT.get(status, 0.0))
            for rowid_pk, seq, service_id, est_lab, est_bur, status in ops
            if service_id is None
        ]
        lab_alloc = _distribute(target_lab, inhouse)
        bur_alloc = _distribute(target_bur, inhouse_bur)

        for rowid_pk, seq, service_id, est_lab, est_bur, status in ops:
            if service_id is None:
                act_lab = lab_alloc.get(rowid_pk, 0.0)
                act_bur = bur_alloc.get(rowid_pk, 0.0)
                act_ser = 0.0
            else:
                act_lab = 0.0
                act_bur = 0.0
                act_ser = round(ser_by_op.get((wo_id, service_id), 0.0), 2)
            updates.append((act_lab, act_bur, act_ser, rowid_pk))

    cur.executemany(
        "UPDATE operation SET act_atl_lab_cost=?, act_atl_bur_cost=?, "
        "act_atl_ser_cost=? WHERE rowid_pk=?", updates
    )
    conn.commit()

    print(f"  operations updated: {len(updates)}")
    nz = cur.execute(
        "SELECT SUM(CASE WHEN act_atl_lab_cost>0 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN act_atl_bur_cost>0 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN act_atl_ser_cost>0 THEN 1 ELSE 0 END) FROM operation"
    ).fetchone()
    print(f"  operations with non-zero actuals (lab / bur / ser): "
          f"{nz[0]} / {nz[1]} / {nz[2]}")

    # Reconciliation: per-work-order operation actuals must tie to the rollups.
    mism = cur.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT w.wo_id,
                 ROUND(w.act_lab_cost,2) AS wl, ROUND(COALESCE(o.ol,0),2) AS ol,
                 ROUND(w.act_bur_cost,2) AS wb, ROUND(COALESCE(o.ob,0),2) AS ob,
                 ROUND(w.act_ser_cost,2) AS ws, ROUND(COALESCE(o.os,0),2) AS os
          FROM work_order w
          LEFT JOIN (
            SELECT wo_id, SUM(act_atl_lab_cost) ol, SUM(act_atl_bur_cost) ob,
                   SUM(act_atl_ser_cost) os
            FROM operation GROUP BY wo_id) o ON o.wo_id = w.wo_id
        ) t
        WHERE ABS(wl-ol) >= 0.01 OR ABS(wb-ob) >= 0.01 OR ABS(ws-os) >= 0.01
        """
    ).fetchone()[0]
    print(f"  work orders whose operation actuals do NOT tie to the rollup: {mism}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
