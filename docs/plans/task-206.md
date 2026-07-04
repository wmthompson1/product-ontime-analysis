---
title: Ontop Showcase: Capacity Planning
---
# Ontop Showcase: Capacity Planning

## What & Why
Republish the **Capacity Planning** ground-truth layer through the Ontop virtual
knowledge graph, proven end-to-end with depth (a natural-language question →
governed SQLite SQL → SPARQL over the virtual graph → identical answer). This is
the first of three new domains that take the interoperability demo from 3
published governed domains to 6. The Capacity Planning grounding SQL already
exists and is verified runnable; this task publishes it as standards-based OWL +
SPARQL without moving any data, mirroring the existing Showcase 6 (customer-order
demand), which is also a doc-grounded layer with **no** SolderEngine template.

## Done looks like
- Running `python3 poc/ontop-ontology-poc/capacity_planning_parity_check.py`
  prints the governed-SQL numbers beside the SPARQL numbers, shows they match,
  and exits 0 (non-zero on any drift).
- 1–2 headline capacity questions are answered through SPARQL and proven equal to
  the governed SQL run on the same read-only snapshot (e.g. total in-house
  standard load hours, and the busiest work center's total load).
- The offline drift guard (run by `scripts/post-merge.sh`) passes with the new
  showcase registered.
- The POC README documents the new showcase the same way Showcases 5 and 6 are
  documented.

## Out of scope
- No SolderEngine computation_template for capacity (it is a doc-grounded layer;
  ground parity against the governed SQL directly — inventing a template is scope
  creep into the semantic layer).
- No changes to the existing showcases, the Flask/HF Space app, Gradio, or
  ArangoDB.
- No live SPARQL HTTP endpoint for this domain (the existing endpoint showcase is
  enough); keep the JVM parity check standalone (do NOT add it to post-merge.sh).
- No edits to the synthetic data or the grounding SQL beyond confirming it runs.

## Steps
1. **Confirm the grounding target** — run the Capacity Planning grounding SQL
   against the live DB read-only and capture the exact headline numbers the
   SPARQL parity will be asserted against.
2. **Author the vocabulary** — a small OWL ontology in its own namespace
   (e.g. `…/capacity#`) with the capacity classes (operation as a routing/load
   step, the work center/resource) and datatype properties for setup/run hours
   and resource type. Mint it separately from the OEE showcase even though both
   read the `operation` table — separate namespace, separate files.
3. **Author the OBDA mapping + JDBC properties** — restate the grounding query's
   governance (in-house only: outside-service excluded, machine/labor resource
   types only) inside the mapping source SQL, so the published facts already
   encode the WHERE. Give every link property a `range` only (no `rdfs:domain`,
   no inverse) to keep Ontop's SQLite output valid.
4. **Write the SPARQL depth queries** — 1–2 scalar queries (no GROUP BY / no
   OPTIONAL) that restate the headline numbers; for a per-work-center number,
   filter to a specific resource id (mirror the Showcase-6 ATP pattern) and, if a
   non-aggregated value sits beside a SUM, split into two scalar queries and
   combine in Python.
5. **Write the parity check** — model it on the Showcase-6 parity check: snapshot
   the live WAL DB once, point both Ontop and the governed SQL at the SAME
   snapshot, assert equality to floating-point tolerance, exit non-zero on drift.
6. **Register + document** — add the showcase to the drift guard's default
   showcase list so the offline file-vs-file guard covers its columns and vocab;
   validate the Turtle with a throwaway rdflib install (never commit rdflib); add
   a README showcase section. If an Ontop CI workflow exists, add the new check to
   it; otherwise the offline drift guard is the gate.

## Architectural constraints
- Synthetic target dialect is SQLite (`manufacturing.db`); the real SQL Server
  T-SQL is a reference benchmark only.
- Read-only: snapshot first, never query the live WAL file twice, never write it,
  never touch ArangoDB. Reuse the existing snapshot/properties/CSV helpers.
- Ontop+SQLite gotchas: prefer scalar SPARQL; link property `range` only; single
  triple inside any `OPTIONAL`; no `#` comments inside `.obda` `[[ ]]` blocks;
  instance IRIs containing `/` need angle brackets in `.rq` text.
- The new files must be entirely separate from existing showcases (own namespace,
  own `.ttl`/`.obda`/`.properties`).

## Relevant files
- `docs/my-mrp-kb/Capacity_Planning.sqlite.sql`
- `docs/my-mrp-kb/Capacity Planning - Aerospace MRP.md`
- `poc/ontop-ontology-poc/customer_order_demand_parity_check.py`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/mapping/customer_order_demand.obda`
- `poc/ontop-ontology-poc/ontology/customer_order_demand.ttl`
- `poc/ontop-ontology-poc/queries/open_demand_value.rq`
- `poc/ontop-ontology-poc/mapping_drift_check.py:49-67`
- `poc/ontop-ontology-poc/README.md`
- `replit_integrations/ontop_poc_setup.py`
- `replit_integrations/ontop_poc_run_demo.py`