---
name: Outside-service PO↔operation linkage
description: How service POs join to operations and why key drift causes silent cost rollup gaps
---

Outside-service purchase-order lines link to shop operations by the composite
key (wo_id, service_id) — NOT by operation sequence number. If an operation's
`service_id` doesn't match the service on its WO's PO line, the service cost
accrues onto the WO rollup (top-down) but never onto the operation actuals
(bottom-up), producing silent rollup-vs-op-actuals drift that only surfaces
when a reconciliation check sums both layers.

**Why:** hit as latent $-level drift on several WOs; op rows carried stale
service ids from a different service than the PO actually purchased.

**How to apply:** whenever adding/closing service POs or completing WOs with
outside-service ops, verify each in-scope operation's `service_id` matches its
PO line's service before re-running the cost cascade; make reconciliation
fail-closed (op actuals must sum to WO rollup to the cent).

Related: any migration that commits data then runs a derived-data cascade must
run the cascade unconditionally on every invocation (cascade steps are
idempotent fixed points) — gating it on "did this run change anything" breaks
recovery when a prior run died between commit and cascade.
