---
name: WO/operation cost accrual reconciliation
description: How synthetic operation actual costs are reverse-distributed from the work_order rollup truth, and the broken outside-service PO→op tie.
---

# Operation cost accrual ↔ work_order rollup reconciliation

The synthetic `manufacturing.db` builds costs **top-down**: `work_order.act_lab_cost`/`act_bur_cost`
are the TRUTH, computed as `SUM(operation.est_atl_lab_cost × STATUS_WEIGHT[status]) × variance`,
where `variance = 0.92 + crc32(wo_id).random()×0.20` and `STATUS_WEIGHT = C:1.0, S:0.5, Q:0.0`.
`work_order.act_ser_cost` = sum of the WO's **received** outside-service POs. `act_mat_cost` =
sum of `material_issue.total_cost`.

**Rule for populating operation-level actuals so they reconcile to the WO rollup:**
- **Labor/burden**: distribute the WO rollup down to progressed in-house ops (`service_id IS NULL`,
  status C/S) proportional to `est_atl_lab_cost × STATUS_WEIGHT` (the exact basis the rollup is
  built from → sums back exactly). Put the rounding residual on the last progressed op so the
  per-WO sum matches to the cent.
- **Outside-service** (`act_atl_ser_cost`): tie each received outside-service PO to its operation
  via **`(wo_id, service_id)`** and sum its `total_cost` onto that op.

**Why not labor_ticket dollars as the basis:** `labor_ticket.labor_cost` is qty-under-scaled
(seeded as `hours × rate` with NO `× quantity`, while `est_atl_lab_cost` has `× quantity`), so
ticket sums are only ~5–15% of the WO truth and cover ~50% of progressed ops. Driving the dollar
allocation off tickets produces lopsided per-op actuals. Tickets are a grain/coverage signal, not
the dollar basis.

**Why NOT the `PO-S{wo}-{seq}` po_id parse for the outside-service tie:** `operation.sequence_no`
is RE-GAPPED by `regap_and_seed_requirements.py` AFTER the outside-service POs are created, so the
seq encoded in the po_id no longer matches any `operation.sequence_no` (verified: 0 matches).
`(wo_id, service_id)` is unique among outside ops and maps every received PO to exactly one op
with zero orphans → exact reconciliation.

**How to apply:** any migration repopulating operation actuals must use these bases and assign the
per-WO rounding residual to one op, or the "op actuals sum to WO bucket" gate fails. A WO can have
`act_ser_cost > 0` while its outside op is still status Q (the PO receipt, not op status, is the
accrual signal for outside work) — so outside-service accrual keys off the received-PO tie, not op
status.
