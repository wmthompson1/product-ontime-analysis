# Job Entity & Lifecycle

## What & Why
Formalize the Job as a first-class semantic entity aligned with Infor LN / SyteLine semantics: a `Job` class in the ontology, the `forJob` property linking every event and cost row to its job, and explicit job creation/completion functions. Grounding: a Job maps 1:1 to the existing `work_order` — this task models that mapping rather than inventing a parallel table.

## Done looks like
- The ontology gains a `Job` class with lifecycle states aligned to the real WO status vocabulary (unreleased / firmed / released / closed) and `forJob` declared with proper domain/range over the event classes.
- A job module exposes `create_job` and `complete_job` functions layered over `work_order`: create registers a job (new synthetic WO row through the established seeding conventions), complete posts the `post_job_completion` flow at a data-derived close date. Planned orders (WO-PLN-*) are never completable.
- The SKOS/binding layer maps Job → `work_order` so semantic queries resolve "job 42" to a wo_id.
- A lifecycle trace query shows, for any job: creation, every cost event in order, and completion — proven by a gate-style test on a backfilled closed WO.

## Out of scope
- Changing work_order schema or statuses.
- UI for job management.

## Steps
1. **Ontology addition** — Job class + lifecycle states + forJob property, consistent with Task-4 conventions.
2. **Job module** — create/complete functions over work_order with fail-closed guards on status.
3. **Binding + trace test** — Job↔work_order binding entry and a lifecycle trace test.

## Relevant files
- `poc/ontop-ontology-poc/ontology/`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/tests/`
