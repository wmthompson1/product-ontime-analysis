# Expand the virtual graph coverage

## What & Why
The Ontop showcase only publishes `purchase_order` and `receiving` (the on-time
delivery + supplier rating story). To prove the interoperability layer scales
beyond one metric, add a second governed showcase to the virtual graph — another
metric the semantic layer already defines (e.g. an OEE template / the `operation`
table) — as ontology terms + OBDA mapping + SPARQL queries, and prove it answers
the same governed number SolderEngine produces. This is the README's "the full
schema — only purchase_order and receiving for this showcase" later step.

## Done looks like
- A second governed metric is published through the virtual graph: new ontology
  class(es)/property(ies), OBDA mapping rows, and at least one SPARQL query.
- A parity check proves the new metric answered over SPARQL matches the number
  SolderEngine assembles from its computation template on the same read-only
  snapshot (to floating-point tolerance), exiting non-zero on drift.
- The offline mapping drift guard covers the new mapping columns/terms too.
- README gains a new "Showcase" section describing the added metric and updates
  the "Out of scope" note about schema coverage.

## Out of scope
- Covering the entire 33-table schema — one additional governed metric is enough
  to prove it scales.
- Auto-generating the mapping (separate task).
- Authentication, deployment, or wiring into the running app/Gradio.

## Steps
1. **Pick + model the metric** — Choose an existing semantic-layer metric with a
   computation template and add its ontology vocabulary terms.
2. **Mapping + queries** — Add the OBDA mapping rows binding the new terms to the
   governed source columns, plus SPARQL query file(s) that exercise it.
3. **Parity check** — Prove the SPARQL answer equals the SolderEngine-assembled
   number on the same snapshot; fail closed on mismatch.
4. **Drift guard + docs** — Extend the offline drift guard to the new terms and
   document the new showcase in the README.

## Relevant files
- `poc/ontop-ontology-poc/ontology/on_time_delivery.ttl`
- `poc/ontop-ontology-poc/mapping/on_time_delivery.obda`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/rating_parity_check.py`
- `poc/ontop-ontology-poc/mapping_drift_check.py`
- `replit_integrations/graph_metadata.json`
- `poc/ontop-ontology-poc/README.md:384-395`
