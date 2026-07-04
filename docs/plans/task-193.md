---
title: v16: rename elevates → RESOLVES_TO
---
# v16 RESOLVES_TO Rename

## What & Why
Rename the column→concept semantic predicate from `elevates` to **`RESOLVES_TO`** and fully purge `elevates` from the graph, parsers, exporter, tests, and docs. This is the v16 schema bump. `RESOLVES_TO` becomes the single, unified edge type that connects any physical node (table column) to a concept node — there is no separate edge type for special cases. `MAPS_TO_CONCEPT` (table→concept) is deliberately left untouched, and `RESOLVES_TO` was chosen over `MAPS_TO` specifically to avoid colliding with it. This is a pure rename: edge counts and graph shape do not change (still 289 nodes / 282 edges, 20 semantic edges) — only the predicate name changes.

**Architectural constraint — unified bridge:** `RESOLVES_TO` is the ONLY edge connecting physical nodes to concept nodes. When UDF/polymorphic work lands in a later milestone, those column→concept mappings will also be `RESOLVES_TO` edges that simply carry heavier edge properties (e.g. `discriminator_clause`, `native_data_type_code`) — NOT a separate `bindings`/`udf_` edge type. Plan and document the rename with this unified bridge in mind, but do not build any UDF behavior here.

**Architectural constraint — SUPPRESSES is a weight, not an edge type:** suppression is represented as a negative/zero weight on the same semantic edge (weight 1/2 = resolve, 0/−1 = suppress), handled in the solder engine and reasoning layer. There is no `suppresses` edge type. Keep the name `SUPPRESSES` as the conceptual term, but it now operates on `RESOLVES_TO` edges. Update the prose/docstrings accordingly; do not introduce a new edge type for it.

## Done looks like
- The semantic predicate is `RESOLVES_TO` everywhere it is live: stored edge_type value, app routing, authoring path, UI dropdowns, bridge health, solder engine, reasoning layer, AQL ground-truth, and the live ArangoDB graph.
- `elevates`/`ELEVATES` no longer appears as a live predicate anywhere outside frozen historical snapshots; a grep gate prevents it from creeping back.
- The exporter emits `RESOLVES_TO`, `SCHEMA_VERSION` is bumped to 16, and `graph_metadata.v16.json` is frozen. All generated artifacts (JSON, SQL dump, TSV, CSVs) regenerate cleanly and pass the parity gates.
- The live ArangoDB graph holds 20 `RESOLVES_TO` semantic edges and zero `elevates` edges; SQL↔AQL parity strict-passes.
- `bash scripts/post-merge.sh` exits 0; both apps boot; node/edge counts are unchanged (289 / 282).
- Docs (canonical spec, MRP knowledge base, AQL query references, integration guide) describe `RESOLVES_TO` as the unified physical-node→concept edge and note the deferred-UDF design intent.

## Out of scope
- All UDF / `user_def_fields` polymorphism, the `bindings` edge collection, the `fie_/udf_/int_/con_` key-prefix scheme, and the `DATA_TYPE` type resolver (deferred to a later milestone).
- Migrating the public repo onto pod22's topology (`fields`/`concepts` collections, lowercase 5-dim keys). pod22 is set aside for now.
- Any change to `MAPS_TO_CONCEPT` / `CAN_MEAN` (table→concept) — untouched.
- The SQLMesh graph-load coupling work (tracked separately).
- The sqlmesh/sqlglot downgrade (tabled by the user).
- Rewriting frozen historical snapshots (`graph_metadata.v1..v15.json`) or historical plan YAMLs.
- English-word false positives that are NOT the predicate: CSS box-shadow `elevation`, the NCM material-"elevation" workflow, `ELEVATED_Work_Order_Status_Report.sql`, and "Learn Python" study files — leave all of these alone.

## Steps
1. **Lock the token forms.** Use `resolves_to` as the stored edge_type value (lowercase, matching `has_column`/`references`) and `RESOLVES_TO` as the display/predicate/UI token. The 3-letter predicate code inside edge unique_ids changes from `ELE` to `RES`, which re-keys all 20 semantic edges — so the live graph migration is a delete-old-key + insert-new-key reload, not an in-place field update.
2. **Update DDL + add a rebuild migration.** `elevates` is hard-coded in `CHECK(edge_type IN (...))` constraints on two tables in four DDL copies. SQLite cannot alter a CHECK in place, so add a table-rebuild migration and update every DDL copy plus the app's boot guards.
3. **Update the exporter.** Emit `resolves_to`, bump `SCHEMA_VERSION` 15→16, set a new `MILESTONE_NAME`, and freeze `graph_metadata.v16.json`.
4. **Update the seeder** so it seeds `resolves_to` edges idempotently; keep it wired into the post-merge gate.
5. **Update the runtime layers** — app routing and supported-predicates list, the SQLite-first authoring path, UI dropdowns, bridge health, solder engine, and the reasoning layer — to speak `RESOLVES_TO`. Re-word `SUPPRESSES` prose to describe it as a weight on `RESOLVES_TO`.
6. **Migrate the live ArangoDB graph and AQL.** Reload the 20 semantic edges under the new predicate/keys, update AQL routing and both copies of the AQL path-resolution ground-truth file. Verify which collection actually stores the edges (single `manufacturing_graph_edge` with an edge_type field, and any separately-named `elevates` collection used by the authoring/commit path) and cover both.
7. **Regenerate all generated artifacts** (graph metadata JSON, SQL dump, triples TSV, edge CSVs) from the exporter; never hand-edit them.
8. **Update the mockup UI** (Define Relationship + Graph Triple components and their tests) to offer/assert `RESOLVES_TO`, and rebuild the static bundle.
9. **Update tests** that assert `elevates`/`ELEVATES` to assert `RESOLVES_TO`, including the SQL-graph, authored-edges, commit-edge, solder-validation, coverage-gap, and parity tests.
10. **Add an anti-regression grep gate** (mirroring the existing legacy-perspective gate) that fails on any new `elevates`/`ELEVATES` literal outside the frozen `*.vNN.json` snapshots and historical plan docs. Verify the parity checkers stay predicate-agnostic and need no change.
11. **Update docs** (canonical construction spec with a v16 decision-log entry, MRP knowledge base, both AQL query references, integration guide) to describe `RESOLVES_TO` as the unified physical-node→concept edge, and record the deferred-UDF intent (future UDF columns reuse `RESOLVES_TO` with heavier edge properties). Do NOT touch pod22.
12. **Run the full gate and verify.** `bash scripts/post-merge.sh` must exit 0, both apps must boot, SQL↔AQL parity must strict-pass, and counts must be unchanged at 289 nodes / 282 edges with 20 `RESOLVES_TO` edges.
13. **Cross-repo note.** The private Windows/SQL Server repo mirrors this structure (repo-duality) and must apply the same rename there: SQL Server DDL CHECK constraints, the private exporter/seed equivalents, AQL routing, and the live-graph reload. That mirroring happens in the private repo and is outside this repo's executable scope — flag it for the architect.
14. **Update memory** (in build mode) so the column→concept predicate is recorded as `RESOLVES_TO` (universal physical→concept bridge), and note that `elevates` is retired as of v16.
15. **Architect code review** of the full diff before completion.

## Relevant files
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/seed_elevations.py`
- `replit_integrations/load_canonical_to_arango.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/sql_graph_tables.sql`
- `replit_integrations/graph_triples.tsv`
- `replit_integrations/graph_metadata_edges.csv`
- `replit_integrations/arango_graph_edges.csv`
- `replit_integrations/graph_metadata_canonical_example.json`
- `replit_integrations/graph_metadata_canonical_example.md`
- `hf-space-inventory-sqlgen/app.py`
- `hf-space-inventory-sqlgen/semantic_reasoning.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/bridge_health.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/migrations/add_sql_graph_tables.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/026_AQL_Path_Resolution_Test.aql`
- `026_AQL_Path_Resolution_Test.aql`
- `hf-space-inventory-sqlgen/scripts/bridge_policy_verify.py`
- `hf-space-inventory-sqlgen/scripts/check_legacy_perspective_refs.py`
- `persist_semantic_graph_to_arango.py`
- `refresh_arango_from_sqlite.py`
- `scripts/post-merge.sh`
- `scripts/verify_metadata_meaning.py`
- `scripts/check_arango_state.py`
- `tests/test_sql_graph_tables.py`
- `tests/test_authored_edges_merge.py`
- `tests/test_sql_aql_parity.py`
- `tests/test_semantic_scaffolding.py`
- `hf-space-inventory-sqlgen/tests/test_commit_edge_sqlite_first.py`
- `hf-space-inventory-sqlgen/tests/test_commit_edge_duplicate.py`
- `hf-space-inventory-sqlgen/tests/test_commit_edge_success.py`
- `hf-space-inventory-sqlgen/tests/test_sweep1_coverage_gaps.py`
- `hf-space-inventory-sqlgen/tests/test_resolution_messages.py`
- `hf-space-inventory-sqlgen/test_solder_validation.py`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.history.test.ts`
- `artifacts/mockup-sandbox/src/components/mockups/graph-triple/GraphTriple.tsx`
- `docs/canonical_graph_construction_concept_as_node.md`
- `docs/mrp_inventory_knowledge_base.md`
- `docs/arango_graph_queries.md`
- `docs/arango_graph_queries_new.md`
- `define-relationship-integration-guide.md`