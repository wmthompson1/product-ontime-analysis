# `-- Binding:` marker dependencies — fleet work packages + SME approvals

*Saved from chat, 2026-07-06. Goal: activate the seeded fast-path in the
Ontology Mosaic lenses for the 11 chain-reachable ground-truth queries.*

## What a binding needs (3 pieces per query)

1. A `-- Binding: <binding_key>` line under the query's `-- Query:` marker
   in its `app_schema/queries/*.sql` file
2. That binding key present in `reviewer_manifest.json` (an SME-approved snippet)
3. The snippet `.sql` file on disk — seeding into `sql_view_ontology` is
   optional (the lens extracts live from the snippet if unseeded)

## Group A — Ready to bind (snippet exists, just add the marker): 3 queries

All three in `receivables.sql`, concept **OrderAccountingState**:

- Customer AR Exposure
- Open Order Backlog Aging
- Order Revenue Recognition Status

Candidate snippet: `payables_purchaseorderstatus_20260601_000005`
(anchor ORDERACCOUNTINGSTATE) — **but it's a Payables-perspective PO-status
view**. SME decision needed: confirm it fits the receivables side, or approve
new receivables-side snippets instead.

## Group B — Blocked on a missing snippet: 3 queries

All three in `supplier_performance.sql`, concept **ThreeWayMatchState**:

- AP Aging by Supplier
- Supplier AP Total Due
- Three-Way Match Exceptions

**No THREEWAYMATCHSTATE anchor exists in the manifest at all** — the fleet
must draft a three-way-match snippet and the SME must approve it into the
manifest before these can bind.

## Group C — Query text missing from the governed files entirely: 5 queries

These exist in the intent wiring but have **no `-- Query:` marker anywhere**,
so the lenses currently show "not found in the governed files." Fleet must
author (or rename-align) the query text, plus description and binding:

| Query name (must match exactly) | Concept | Approved snippet candidates |
|---|---|---|
| Supplier delivery scorecard | DeliveryPerformanceSupplier | `suppliers_supplierscorecard_20260601_000001`, `quality_deliveryperformancesupplier_20260208_160002/160008` |
| Late delivery penalty calculation | DeliveryPerformanceFinance | `payables_openpobysupp_20260601_000006`, `finance_deliveryperformancefinance_20260208_160003` |
| Weekly defect rate trend | DefectSeverityQuality | `quality_defectseverityquality_20260208_150100/160004/160006` |
| Defects by severity with cost rollup | DefectSeverityCost | `finance_ncm_cost_20260208_150000`, `finance_defectseveritycost_20260208_160014` |
| Customer escape risk analysis | DefectSeverityCustomer | `customer_defectseveritycustomer_20260208_150200` |

Note: near-miss names already exist ("Supplier Scorecard", "Supplier Cost
Penalties", "Daily Defect Rate by Product Line") — the fleet can either add
new markers with the exact intent-wired names, or the SME can bless renaming,
since the lookup is an exact name match.

## Housekeeping items

- `crm_customer.sql` and `customer_order.sql` sit in `app_schema/queries/`
  but aren't in `index.json` and carry no markers — invisible to the chain.
  If Group C queries land in new files, `index.json` needs entries.
- Only the 7 inventory views are seeded in `sql_view_ontology`; seeding the
  newly bound queries is optional polish (live extraction already labels
  itself "not yet seeded").

## Bottom line for SME scheduling

Two approval decisions (Group A perspective fit, Group B new three-way-match
snippet) and one blessing on name alignment for Group C.
