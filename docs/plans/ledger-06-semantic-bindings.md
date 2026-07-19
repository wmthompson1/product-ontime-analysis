# Bind Ledger Ontology to the Semantic Layer

## What & Why
Connect the three layers so natural-language questions can reach the ledger: SKOS concepts → ledger tables, RDF events → posting records, JSON-LD → the semantic graph. Also register the new ledger tables in the app's SQL graph so they're visible in the Schema Browser and pass parity gates.

## Done looks like
- The five ledger tables are registered as nodes (tables + columns) with `contains`/`references` structural edges in the `sql_graph_nodes`/`sql_graph_edges` tables; `graph_metadata.json` re-frozen with a `SCHEMA_VERSION` bump; `sql_graph_parity_check.py` passes (the authoritative gate — live-Arango parity stays out of scope per its known drift).
- `field_descriptions.csv` and `table_descriptions.csv` gain entries for every new column/table; the field-description coverage check passes (each node described exactly once, overlay-only — never written onto graph nodes).
- A binding map (SKOS concept URI → table, RDF event class → gl_events event_type) is stored queryably (SQLite table or committed JSON consistent with existing binding-bridge patterns in the Ontop POC) and exposed read-only to the app.
- Ontop mapping extended so the ledger tables are queryable over SPARQL through the existing POC endpoint, following its generated-mapping pattern.
- All `post-merge.sh` parity and grep gates pass.

## Out of scope
- Natural-language query registration (Task 8).
- Job entity modeling (Task 7).

## Steps
1. **SQL graph registration** — nodes, edges, descriptions, re-freeze, gates green.
2. **Binding map** — concept↔table and event↔posting bindings, stored and exposed read-only.
3. **Ontop mapping extension** — add ledger tables to the POC mapping and verify with a SPARQL smoke query per table.

## Relevant files
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/field_description_coverage_check.py`
- `field_descriptions.csv`
- `table_descriptions.csv`
- `poc/ontop-ontology-poc/generate_mapping.py`
- `poc/ontop-ontology-poc/binding_bridge.json`
- `scripts/post-merge.sh`
