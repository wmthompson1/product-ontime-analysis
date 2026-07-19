# Job-Costing Ledger (RM → WIP → FG)

## What & Why
Materialize the canonical job-costing flow (Raw Materials → WIP → Finished Goods) as a small synthetic GL/job-cost ledger in `manufacturing.db`, deterministically backfilled from the event data that already exists (`material_issue`, `labor_ticket` labor + burden, `work_order` completions, `inventory_transaction`). This gives the SKOS/RDF job-costing ontology (endurants = inventory accounts; perdurants = cost-accumulation events) real physical columns to bind to in a later ontology-layer task, and makes "cost in WIP" an answerable ground-truth query. Terminology follows the Infor-style flow from the user's Example Taxonomy and Ontology document: Material Issued → Labor Applied → Overhead Applied → Job Completion.

## Done looks like
- New `gl_account` reference table seeded with the endurant accounts: Raw Materials Inventory, WIP Inventory, Finished Goods Inventory (with alt labels Inventory / WIP / FG).
- New `job_cost_entry` ledger table: one row per costing event, double-sided (debit/credit account), typed by cost element (material_issued, labor_applied, overhead_applied, job_completion), keyed back to its source row (material_issue.issue_id, labor_ticket.ticket_id, work_order.wo_id) and to the job (wo_id).
- Deterministic backfill: every material issue posts RM→WIP at `total_cost`; every labor ticket posts two WIP debits (labor at `labor_cost`, overhead at `burden_cost`); every closed work order posts WIP→FG for the job's accumulated cost on its close date. AS_OF-anchored dates from the source rows only — never wall-clock.
- Fail-closed verify: WIP nets to exactly zero for every closed job; open/released jobs carry WIP balance equal to their accrued cost; ledger totals reconcile to the source tables to the cent; migration is idempotent (safe double-run).
- Migration wired into the bootstrap chain and a gate-style test file added to the post-merge suite; all existing gate tests still pass.
- Structural FKs declared for the new tables and the frozen graph re-exported (schema version bump) with field/table descriptions covered, mirroring how the receivables tables were added.

## Out of scope
- COGS (no shipment costing exists yet — flow stops at Finished Goods).
- The ontology/SKOS overlay layer itself (JSON-LD mirroring, concept nodes, resolves_to bindings) — a follow-on task once the ledger is in place.
- Any changes to inventory quantities or MRP behavior — the ledger is a read-side costing view; planned orders (WO-PLN-*) have no cost events and get no ledger rows.

## Steps
1. **Schema + seed** — Create `gl_account` (seeded RM/WIP/FG rows) and `job_cost_entry` with debit/credit account references, cost-element type, source-row keys, amount, and entry date.
2. **Deterministic backfill** — Post material issues, labor tickets (labor and burden as separate entries), and closed-job completions from existing rows; completion amount = the job's accumulated WIP.
3. **Fail-closed verify + idempotency** — Zero-WIP check for closed jobs, cent-exact reconciliation to source tables, safe re-run semantics.
4. **Integration** — Wire into the bootstrap chain, add a gate test to the post-merge suite, declare structural FKs, re-freeze the graph with description coverage.

Note: labor and burden amounts were previously reconciled top-down from work-order cost truth — the ledger must reconcile against `labor_ticket` as-is, not recompute them.

## Relevant files
- `hf-space-inventory-sqlgen/migrations/add_receivable_tables.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/tests/test_receivable_tables.py`
- `scripts/post-merge.sh`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `field_descriptions.csv`
- `table_descriptions.csv`
