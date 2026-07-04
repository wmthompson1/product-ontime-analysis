---
title: Ontop ontology interoperability POC
---
# Ontop Ontology Interoperability POC

## What & Why
Prove that the existing governed semantic layer (the "Solder Pattern": natural language → SME-approved SQL) can also be published as a **standards-based, interoperable knowledge graph** without moving or copying any data. We do this with **Ontop** (a virtual OBDA engine): it maps the existing SQLite database to a small OWL ontology and answers standard SPARQL queries by rewriting them into SQL on the fly.

The goal is interoperability — a standard vocabulary (OWL classes/properties + hierarchy) and a standard query language (SPARQL) that another enterprise/aerospace system could consume, layered on top of the SQL we already trust. We use **one** existing showcase: the shared on-time delivery definition across the Ops / Supplier / Finance perspectives.

This is a read-only, demo-scoped proof of concept. Nothing is wired into the Flask/HF Space app, the Gradio UI, ArangoDB, or SolderEngine. No graph writes of any kind.

## Done looks like
- A small OWL ontology file capturing the on-time delivery concept, the two physical entities it relates (purchase order, receiving), and at least **one hierarchy relationship** (the three perspectives expressed as sub-concepts/sub-properties of a shared parent) so the standards-based hierarchy angle is demonstrated.
- An Ontop `.obda` mapping file that connects SQL over the existing `manufacturing.db` to the ontology terms — the mapping's source SQL computes the per-delivery on-time score from receipt date vs. required date.
- A runnable, documented demo: a single command/script that runs a SPARQL query computing the on-time delivery rate through the virtual graph.
- A parity check showing the SPARQL answer **matches** the on-time rate produced by SolderEngine's assembled SQL for the same metric (same number, side by side).
- A short README explaining what was proven, the artifacts, exactly how to run it, and the dependency footprint — stating plainly that it is read-only and not part of the running app.

## Out of scope
- Any ArangoDB or graph writes; any change to the Flask app, HF Space, Gradio tabs, or SolderEngine.
- The full schema — only the on-time delivery showcase tables (`purchase_order`, `receiving`, `po_line`).
- Auto-generating the OBDA mapping from the `sql_graph_*` tables / `graph_metadata.json` (a sensible later step to avoid drift, but for this POC the single showcase mapping is hand-authored).
- Stardog or any materialized triplestore; OWL reasoning beyond the lightweight profile Ontop uses for SQL rewriting.
- The undeveloped "KB" knowledge loops — unrelated to this POC's data.

## Steps
1. **Stand up the Ontop toolchain (demo-scoped, isolated).** Install a Java runtime, the Ontop CLI, and a SQLite JDBC driver into a dedicated POC directory; pin and document the versions. All free/open-source, consistent with the cost-conscious, demo-first preference.
2. **Author the minimal OWL ontology.** Define classes for the purchase order and receiving entities, an on-time delivery concept/property, and one hierarchy relationship that expresses the Ops/Supplier/Finance perspectives as sub-concepts of a shared parent.
3. **Author the Ontop `.obda` mapping over `manufacturing.db`.** Write the source SQL that joins receiving → po_line → purchase_order and emits a per-delivery on-time score (receipt date vs. required date), mapped onto the ontology terms. This mapping is the standards-based restatement of the showcase's computation template.
4. **Provide the SPARQL demo plus a parity check.** One command runs a SPARQL query that aggregates the per-delivery scores into the on-time rate; a second path runs SolderEngine's assembled SQL for the same metric and asserts the two results match.
5. **Write the POC README.** Document what was proven, the artifacts, run instructions, and the dependency footprint; state explicitly that it is read-only and not wired into the app.

## Architectural constraints
- Strictly read-only against `hf-space-inventory-sqlgen/app_schema/manufacturing.db`; the SQLite file is WAL-mode and gitignored — open it read-only and do not trigger writes.
- The on-time definition is the shared computation template `AVG(CASE WHEN {receipt_date} IS NOT NULL AND {receipt_date} <= {required_date} THEN 1.0 WHEN {receipt_date} > {required_date} THEN 0.0 ELSE NULL END)` with bindings `receipt_date → receiving.receipt_date` and `required_date → purchase_order.required_date`. The mapping must preserve this exact semantics so the parity check holds.
- Keep all POC artifacts under a single dedicated directory so they are clearly separate from the production app.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app.py:2262-2263`
- `replit_integrations/graph_metadata.json`