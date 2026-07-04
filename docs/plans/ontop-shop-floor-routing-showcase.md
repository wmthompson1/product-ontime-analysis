# Ontop Showcase: Shop Floor Routing

## What & Why
Republish the **Shop Floor Work & Routing** ground-truth layer through the Ontop
virtual knowledge graph, proven end-to-end with depth (a natural-language
question → governed SQLite SQL → SPARQL over the virtual graph → identical
answer). This is the second of three new domains taking the interoperability demo
from 3 published governed domains to 6. The routing grounding SQL is an existing
strict two-table join (`work_order` + `operation`); this task publishes it as
standards-based OWL + SPARQL without moving data, mirroring Showcase 6
(customer-order demand), which is also a doc-grounded layer with no SolderEngine
template.

## Done looks like
- Running `python3 poc/ontop-ontology-poc/shop_floor_routing_parity_check.py`
  prints the governed-SQL numbers beside the SPARQL numbers, shows they match,
  and exits 0 (non-zero on any drift).
- 1–2 headline routing questions are answered through SPARQL and proven equal to
  the governed SQL on the same read-only snapshot (e.g. total routing-step run
  hours across work orders, and the routing-step count for one specific work
  order).
- The offline drift guard (run by `scripts/post-merge.sh`) passes with the new
  showcase registered.
- The POC README documents the new showcase like Showcases 5 and 6.

## Out of scope
- No SolderEngine computation_template (doc-grounded layer; ground parity against
  the governed SQL directly).
- The grounding query is a strict two-table join (`work_order` + `operation`); do
  NOT add a third table — the work-station name lives in prose only, matching the
  grounding SQL.
- No changes to existing showcases, the Flask/HF Space app, Gradio, or ArangoDB.
- No live SPARQL HTTP endpoint for this domain; keep the JVM parity check
  standalone (not in post-merge.sh).

## Steps
1. **Confirm the grounding target** — run the routing grounding SQL read-only and
   capture the exact headline numbers the SPARQL parity will assert against.
2. **Author the vocabulary** — a small OWL ontology in its own namespace
   (e.g. `…/routing#`): the work order, the operation as a routing step, and the
   datatype properties for sequence number, operation status, and run/setup
   hours. Mint `:Operation` in this namespace separately from the OEE/capacity
   showcases.
3. **Author the OBDA mapping + JDBC properties** — map the two tables and the
   child→parent routing link (operation → work order) minted on the operation
   row, with a `range` only (no `rdfs:domain`, no inverse).
4. **Write the SPARQL depth queries** — 1–2 scalar queries (no GROUP BY / no
   OPTIONAL); for a per-work-order number, filter to a specific work-order id
   (mirror the Showcase-6 ATP filter pattern).
5. **Write the parity check** — model it on the Showcase-6 parity check: snapshot
   the live WAL DB once, point Ontop and the governed SQL at the SAME snapshot,
   assert equality to tolerance, exit non-zero on drift.
6. **Register + document** — add the showcase to the drift guard's default
   showcase list; validate the Turtle with a throwaway rdflib install (never
   commit rdflib); add a README showcase section. If an Ontop CI workflow exists,
   add the new check to it; otherwise the offline drift guard is the gate.

## Architectural constraints
- Synthetic target dialect is SQLite (`manufacturing.db`); real SQL Server T-SQL
  is reference-only.
- Read-only snapshot pattern; never write the live WAL file; never touch ArangoDB;
  reuse the existing snapshot/properties helpers.
- Ontop+SQLite gotchas: scalar SPARQL preferred; link property `range` only;
  single-triple `OPTIONAL`; no `#` comments inside `.obda` `[[ ]]` blocks; `/` in
  instance IRIs needs angle brackets in `.rq`.
- New files entirely separate from existing showcases (own namespace + files).

## Relevant files
- `docs/my-mrp-kb/Shop_Floor_Routing.sqlite.sql`
- `docs/my-mrp-kb/Shop Floor Work and Routing - Aerospace MRP.md`
- `poc/ontop-ontology-poc/customer_order_demand_parity_check.py`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/mapping/customer_order_demand.obda`
- `poc/ontop-ontology-poc/ontology/customer_order_demand.ttl`
- `poc/ontop-ontology-poc/mapping_drift_check.py:49-67`
- `poc/ontop-ontology-poc/README.md`
- `replit_integrations/ontop_poc_setup.py`
