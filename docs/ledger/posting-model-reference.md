# Posting-Model Reference — the Four GL Posting Functions

Reference for `hf-space-inventory-sqlgen/gl_posting.py`, the entire posting
surface of the synthetic job-costing ledger. Four functions, no others; each
is a thin, deterministic insert path into the `gl_*` tables created by
`migrations/add_gl_ledger_tables.py`.

## The four functions and their table effects

Every posting writes exactly one `gl_events` row plus the ledger lines below.
Amounts are rounded to 2 decimals; inventory lines are **signed** (`+` into
an account, `−` out of it).

| Function | Flow | `gl_events.event_type` | Inventory ledger lines | `gl_job_cost_detail` line |
|---|---|---|---|---|
| `post_material_issue` | RM → WIP | `RM_ISSUE` | `gl_raw_materials_inventory` **−amount**; `gl_wip_inventory` **+amount** | `MATERIAL` |
| `post_labor` | → WIP | `LABOR` | `gl_wip_inventory` **+amount** | `LABOR` |
| `post_overhead` | → WIP | `BURDEN` | `gl_wip_inventory` **+amount** | `BURDEN` |
| `post_job_completion` | WIP → FG | `FG_COMPLETION` | `gl_wip_inventory` **−amount**; `gl_finished_goods_inventory` **+amount** | *(none — completion relieves, it doesn't add cost)* |

Shared signature: `(cur, job_id, part_id, amount, event_date, source_table,
source_id)`. `job_id` is the existing `work_order.wo_id`; all FK clauses on
the `gl_*` tables are structural-only (FK enforcement is OFF project-wide).

## Idempotency

Each posting carries its originating document identity, and the idempotency
key is the triple:

```
(source_table, source_id, event_type)
```

If a `gl_events` row with that triple already exists, the function is a
**no-op and returns `None`** — re-running any backfill creates no duplicates.
The keys used by the deterministic backfill
(`migrations/backfill_gl_ledger.py`):

| Source document | Key | Amount | Event date |
|---|---|---|---|
| `material_issue` row | `(material_issue, issue_id, RM_ISSUE)` | `total_cost` | `issue_date` |
| `labor_ticket` row (labor) | `(labor_ticket, ticket_id, LABOR)` | `labor_cost` | `clock_out` |
| `labor_ticket` row (burden) | `(labor_ticket, ticket_id, BURDEN)` | `burden_cost` | `clock_out` |
| closed `work_order` | `(work_order, wo_id, FG_COMPLETION)` | `act_mat_cost + act_lab_cost + act_bur_cost` | `close_date` |

Note that one labor ticket legitimately produces **two** events (LABOR and
BURDEN) — the `event_type` in the key is what keeps them distinct.

## The no-control-logic design decision

The posting model deliberately has **no control logic**:

- **No period close, no reconciliation, no control accounts, no validation**
  beyond fail-closed argument checks (`amount` must be positive,
  `event_date` is required). Balances are nothing more than signed line
  sums.
- **`event_date` is always caller-supplied and data-derived** from the
  source document (issue date, clock-out, close date) — never wall-clock.
  A source row missing its date fails closed at backfill time rather than
  being silently stamped "now".
- **No transaction control**: functions take an open cursor and never
  commit; the caller owns the transaction. The backfill uses this to run
  its cent-exact tie-out (per-job `gl_job_cost_detail` sums vs.
  `work_order` actual costs) *before* commit and roll back on any drift.
- **Why:** the ledger is a *read-side costing view* of event data that
  already exists elsewhere, not a system of record. Correctness is enforced
  once, fail-closed, at backfill/migration time (zero-WIP for closed jobs,
  cent-exact reconciliation to source tables) — not re-enforced inside every
  posting. Keeping the posting functions control-free keeps them trivially
  auditable, deterministic, and safe to replay, which is exactly what the
  idempotency key needs to guarantee.

Boundaries baked into the model: planned orders (`WO-PLN-*`) and non-closed
work orders are never completed; zero-amount source lines are skipped;
outside-service cost is out of scope; the flow stops at Finished Goods
(no COGS/shipment costing exists).

## Tables (DDL: `migrations/add_gl_ledger_tables.py`)

| Table | Role | Shape notes |
|---|---|---|
| `gl_events` | Event log every ledger line hangs off | `event_id`, `job_id`, `event_type`, `amount`, `event_date`, `source_table`, `source_id` |
| `gl_raw_materials_inventory` | RM ledger lines | signed `amount`; `event_id`/`job_id`/`part_id` linkage |
| `gl_wip_inventory` | WIP ledger lines | same shape; nets to exactly 0 for every closed job |
| `gl_finished_goods_inventory` | FG ledger lines | same shape; flow terminus |
| `gl_job_cost_detail` | Per-job cost register | `event_type` here is the **cost element** (`MATERIAL` / `LABOR` / `BURDEN`), not the posting event type |

See the [job-costing flow diagram](diagrams/job_costing_flow.svg) for the
whole picture at a glance.
