# Job-Costing Ledger — Documentation Index

Documentation tying the whole synthetic job-costing ledger build together —
the ontology, the flow, and the posting model — so an SME or a future agent
can understand the system without reading code.

## The four artifacts

1. **[Ontology diagram](diagrams/ledger_ontology.svg)** — the SKOS concept
   scheme (inventory-account and event-type concepts), the OWL/RDF event
   classes beside it, and the flow properties (`:consumesMaterial`,
   `:addsCostToWIP`, `:producesFinishedGoods`, `:forJob`,
   `:hasLifecycleState`) tying the layers together.
   Source: [`diagrams/ledger_ontology.dot`](diagrams/ledger_ontology.dot).
2. **[Job-costing flow diagram](diagrams/job_costing_flow.svg)** — the cost
   flow Raw Materials → WIP → Finished Goods, annotated with the four
   posting events, their signed table effects, and the side-registers
   (`gl_events`, `gl_job_cost_detail`).
   Source: [`diagrams/job_costing_flow.dot`](diagrams/job_costing_flow.dot).
3. **[JSON-LD concept reference](jsonld-concept-reference.md)** — every
   concept in `ledger_skos.jsonld` with its label, definition, notation, and
   physical-table binding (or deliberate unboundness).
4. **[Posting-model reference](posting-model-reference.md)** — the four
   posting functions in `gl_posting.py`, their table effects, the
   `(source_table, source_id, event_type)` idempotency key, and the
   no-control-logic design decision.

## Regenerating the diagrams

The diagrams are generated deterministically from committed Graphviz
sources — never hand-edit the SVGs. After any change to the ontology files
(`poc/ontop-ontology-poc/ontology/ledger_skos.jsonld`,
`poc/ontop-ontology-poc/ontology/ledger_events.ttl`) or the posting model
(`hf-space-inventory-sqlgen/gl_posting.py`,
`migrations/backfill_gl_ledger.py`), update the `.dot` sources to match and
re-render:

```bash
docs/ledger/diagrams/render.sh     # requires graphviz (dot)
```

## The simplified-GL design rationale

This is deliberately **not** a real general ledger. There are no journal
headers, no chart of accounts, no debit/credit pairs, no period close, no
control accounts, and no reconciliation machinery inside the posting path.
The ledger is a *read-side costing view*: five minimal `gl_*` tables whose
signed line amounts are deterministically backfilled from operational
documents that already exist (`material_issue`, `labor_ticket`, closed
`work_order` rows), with every event date data-derived from its source
document — never wall-clock. Correctness is enforced once, fail-closed, at
migration time (zero-WIP for every closed job; cent-exact tie-out of job
cost detail against work-order actuals; idempotent replay), not re-checked
inside every posting. The flow intentionally stops at Finished Goods —
no COGS or shipment costing exists yet. This keeps the ledger small enough
to bind cleanly to the SKOS/OWL ontology layer and trivially auditable end
to end, which is the point of the exercise: real physical columns for the
semantic layer, not a bookkeeping system.

## Underlying sources (the truth this page documents)

- `poc/ontop-ontology-poc/ontology/ledger_skos.jsonld` — SKOS concept scheme
- `poc/ontop-ontology-poc/ontology/ledger_events.ttl` — OWL event classes + flow properties
- `poc/ontop-ontology-poc/ledger_binding_map.json` — governed ontology↔table binding map
- `hf-space-inventory-sqlgen/gl_posting.py` — the four posting functions
- `hf-space-inventory-sqlgen/migrations/add_gl_ledger_tables.py` — `gl_*` DDL
- `hf-space-inventory-sqlgen/migrations/backfill_gl_ledger.py` — deterministic backfill
- `hf-space-inventory-sqlgen/skos_ledger.py` / `ledger_bindings.py` — fail-closed loaders
