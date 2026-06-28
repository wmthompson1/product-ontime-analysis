---
name: Synthetic ERP backfill grounding
description: How empty/zero columns in the synthetic ERP must be filled — derived from the real transactional flow, deterministic, never random.
---

# Synthetic ERP backfill grounding

When the synthetic manufacturing ERP (`hf-space-inventory-sqlgen/app_schema/manufacturing.db`)
ships columns that read blank/zero on dashboards, backfill them by **deriving values from the
existing transactional flow**, never by inventing random numbers.

**The flow is the source of truth** (mirrors the private SQL-Server model in `Data_Models/Payables/`
and the three-way-match: PO *contractual* → RECEIVER *physical* → PAYABLE *financial*):

- **Supplier performance** = a scorecard over *receiving* history: on-time delivery
  (`receipt_date <= purchase_order.required_date`, the canonical DESIRED_RECV_DATE; ignore NULL
  required dates) blended with quality acceptance (`inspection_status`: Passed/Waived good, Failed
  bad, Pending excluded). Recompute *all* suppliers so the column is one explainable function.
- **Work-order actual cost** = job costing assembled per WO from real sources, recognized at the
  right event, not at order time:
  - labor/burden = operation est cost weighted by **operation progress** (C=1.0, S=0.5, Q=0.0) ×
    a deterministic per-WO variance — so not-started WOs (all ops Q) accrue 0, matching
    `backfill_operation_progress.py`.
  - outside service = sum of the WO's `outside_service` POs **that have a receiving row** (cost at receipt).
  - material = sum of `material_issue.total_cost` for the WO (actually issued).

**Why:** the user explicitly requires supply-side grounding (not random), and grounded values
let every dashboard number be traced back to a source row (external buckets must tie to their
source SQL to the penny).

**How to apply:** write these as idempotent migrations under
`hf-space-inventory-sqlgen/migrations/` in the house style — `crc32(key)`-seeded `Random` for any
variance (process-independent), values as pure functions of current rows so re-running reproduces
identical output, UPDATE by primary key only. SQLite is WAL-mode + gitignored: checkpoint
(`PRAGMA wal_checkpoint(TRUNCATE)`) before trusting the main file. Touch SQLite only — never the
certified ArangoDB graph.
