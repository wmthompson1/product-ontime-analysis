# Map Posting Functions to RDF Events

## What & Why
Give every ledger posting a semantic trace: each of the four posting functions emits a corresponding RDF event (MaterialIssueEvent, LaborApplicationEvent, OverheadApplicationEvent, JobCompletionEvent) with its flow properties, so the ontology can explain what each posting did to the inventory buckets.

## Done looks like
- Each posting function records an event: persisted deterministically in the `gl_events` table (event_type = RDF class local name, plus job/amount/timestamp/source linkage) so events survive restarts and are replayable.
- A serializer renders `gl_events` rows as RDF triples (event instance, `forJob`, `consumesMaterial`/`addsCostToWIP`/`producesFinishedGoods` per event type) matching the Task-4 ontology — deterministic IRIs derived from idempotency keys, no random UUIDs.
- The backfilled ledger yields a complete event trace: one event per posted source document; a check proves 1:1 correspondence between `gl_job_cost_detail` rows and events, failing closed on gaps.
- Gate-style test covering each event type's emitted triples.

## Out of scope
- SPARQL endpoint exposure / Ontop mapping (Task 6).
- New posting types.

## Steps
1. **Event persistence** — wire event recording into the posting functions using `gl_events` with the RDF class vocabulary.
2. **RDF serializer** — deterministic triple rendering of events per the ontology.
3. **Trace completeness check + test** — 1:1 posting↔event verification and per-class serialization tests.

## Relevant files
- `poc/ontop-ontology-poc/ontology/`
- `hf-space-inventory-sqlgen/tests/`
