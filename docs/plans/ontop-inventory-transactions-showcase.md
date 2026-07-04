# Ontop Showcase: Inventory Transactions

## What & Why
Republish the **Inventory Transactions** ground-truth layer through the Ontop
virtual knowledge graph, proven end-to-end with depth (a natural-language
question → governed SQLite SQL → SPARQL over the virtual graph → identical
answer). This is the third of three new domains taking the interoperability demo
from 3 published governed domains to 6. The inventory-transactions grounding SQL
(the "AI Review" query) already exists; this task publishes it as standards-based
OWL + SPARQL without moving data, mirroring Showcase 6 (customer-order demand),
which is also a doc-grounded layer with no SolderEngine template.

## Done looks like
- Running `python3 poc/ontop-ontology-poc/inventory_transactions_parity_check.py`
  prints the governed-SQL numbers beside the SPARQL numbers, shows they match,
  and exits 0 (non-zero on any drift).
- 1–2 headline inventory questions are answered through SPARQL and proven equal to
  the governed SQL on the same read-only snapshot (e.g. a net/total movement
  quantity across transactions, and a per-part net quantity for one specific
  part).
- The offline drift guard (run by `scripts/post-merge.sh`) passes with the new
  showcase registered.
- The POC README documents the new showcase like Showcases 5 and 6.

## Out of scope
- No SolderEngine computation_template (doc-grounded layer; ground parity against
  the governed SQL directly).
- No changes to existing showcases, the Flask/HF Space app, Gradio, or ArangoDB.
- No live SPARQL HTTP endpoint for this domain; keep the JVM parity check
  standalone (not in post-merge.sh).

## Steps
1. **Inspect + confirm the grounding target** — read the inventory-transactions
   grounding SQL to learn the exact table(s), columns, and transaction-type
   vocabulary it uses, run it read-only, and capture the headline numbers the
   SPARQL parity will assert against.
2. **Author the vocabulary** — a small OWL ontology in its own namespace
   (e.g. `…/inventory#`): the inventory transaction (and part, if the grounding
   SQL joins one) plus datatype properties for transaction quantity and
   transaction type.
3. **Author the OBDA mapping + JDBC properties** — map the transaction table (and
   any part link minted on the transaction row, with a `range` only — no
   `rdfs:domain`, no inverse). Restate any governance filter from the grounding
   SQL inside the mapping source SQL.
4. **Write the SPARQL depth queries** — 1–2 scalar queries (no GROUP BY / no
   OPTIONAL); for a per-part number, filter to a specific part id (mirror the
   Showcase-6 ATP filter pattern). If signed/netting math is involved, keep each
   SPARQL query scalar and combine in Python.
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
- `docs/my-mrp-kb/kb-inventory-transactions/Inventory_-_Transactions_AI_Review.sqlite.sql`
- `docs/my-mrp-kb/kb-inventory-transactions/Inventory_Transaction_Terminology_Guide.md`
- `docs/my-mrp-kb/kb-inventory-transactions/Inventory_Transaction_Entry_Index.md`
- `poc/ontop-ontology-poc/customer_order_demand_parity_check.py`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/mapping/customer_order_demand.obda`
- `poc/ontop-ontology-poc/ontology/customer_order_demand.ttl`
- `poc/ontop-ontology-poc/mapping_drift_check.py:49-67`
- `poc/ontop-ontology-poc/README.md`
- `replit_integrations/ontop_poc_setup.py`
