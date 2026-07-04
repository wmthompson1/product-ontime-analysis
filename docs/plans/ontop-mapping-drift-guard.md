# Ontology/Mapping Drift Guard

## What & Why
The POC's ontology (`.ttl`) and OBDA mapping (`.obda`) are hand-authored and
reference physical tables/columns (e.g. `receiving.receipt_id`,
`purchase_order.required_date`, `suppliers.performance_rating`). If the governed
schema renames or drops one of those, the mapping silently breaks and the
virtual graph quietly disagrees with the SQL source of truth. Add a
deterministic, offline drift check that proves the mapping + ontology stay
aligned with the governed schema (the committed `graph_metadata.json`), and wire
it into the same post-merge gate the rest of the project uses. This is the
lightweight cousin of full mapping auto-generation (which stays out of scope).

## Done looks like
- The check reports PASS when every physical table/column the mapping reads
  exists in the governed schema, and FAILS (non-zero exit) with a clear diff
  naming the offending table/column when one drifts.
- It also confirms every ontology term used as a mapping target is declared in
  the ontology, and every mapped class/data property has at least one backing
  mapping (no dangling vocabulary), in either direction.
- It runs with no database and no network — file-vs-committed-schema only — like
  the existing field-description coverage gate.
- It is wired into the project's post-merge check sequence so drift is caught
  automatically, guarded so a missing schema/toolchain degrades gracefully.
- The POC README no longer lists drift detection under "Out of scope"; a short
  note documents the new gate.

## Out of scope
- Auto-generating the `.obda` mapping from the schema (validation only, not
  generation).
- Validating against the live SQLite DB or ArangoDB (file-vs-committed-schema
  only).
- Expanding the mapping to more tables.

## Steps
1. **Extract references** — Parse each mapping's source SQL with SQLGlot and
   resolve every base table/column it reads (seeing through aliases, CASE
   expressions, and joins), plus collect the ontology terms each mapping targets.
2. **Validate against the governed schema** — Assert every referenced
   table/column exists as a column node in the committed schema snapshot; emit a
   precise diff on any miss.
3. **Validate vocabulary closure** — Assert every mapping target term is declared
   in the ontology, and every declared class/data property is backed by at least
   one mapping; flag dangling terms either way.
4. **Reporting + exit code** — Print a readable PASS/FAIL report and exit
   non-zero on any drift, mirroring the existing coverage/parity checkers.
5. **Wire into the gate** — Add the check to the post-merge sequence so it runs
   on every merge.
6. **Docs** — Update the POC README to describe the gate and drop drift
   detection from "Out of scope".

## Relevant files
- `poc/ontop-ontology-poc/mapping/on_time_delivery.obda`
- `poc/ontop-ontology-poc/ontology/on_time_delivery.ttl`
- `poc/ontop-ontology-poc/README.md:199-210`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/field_description_coverage_check.py`
- `replit_integrations/sql_graph_parity_check.py`
- `scripts/post-merge.sh`
