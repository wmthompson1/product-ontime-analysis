# Align FK Modeling to Canonical

## What & Why
The canonical graph-metadata model (defined by `replit_integrations/export_graph_metadata.py` and documented in `graph_metadata_canonical_example.md`/`.json`) represents foreign keys two ways:
- **`foreign_key`** — a boolean attribute on the **column node** itself.
- **`references`** — a structural **edge** (`edge_family: structural`, `edge_type: references`, `perspective: system`) connecting the **child column node → parent column node**, carrying `references_table` / `references_column` properties.

There is **no `FOREIGN_KEY` edge type**. Several places in the active codebase still treat `FOREIGN_KEY` as an edge/predicate, or store the FK flag as an edge property named `is_foreign_key` instead of a node attribute named `foreign_key`. This task brings those surfaces into line with the canonical model so the frontend, fixtures, tests, and planning docs all describe FK the same way the exporter emits it.

## Done looks like
- No active code treats `FOREIGN_KEY` as an edge type, predicate, or edge collection.
- The FK boolean is consistently named **`foreign_key`** and lives on the **column node** (the name `is_foreign_key` is retired across the active codebase).
- Child→parent FK relationships are described only via the `references` edge, matching the exporter's output (structural family, `references` type, `references_table`/`references_column` props).
- The define-relationship / triple-builder frontend offers `references` (not `FOREIGN_KEY`) as the FK relationship, and any self-loop guard is keyed off the correct predicate.
- ArangoDB fixtures and AQL demos/tests read the FK flag from the column node (`foreign_key`) and traverse `references` edges for child→parent links.
- Planning docs (`plan-012`) no longer list `FOREIGN_KEY` as a structural edge type.
- The Solder catalog test accounts for `references` topology, not only `contains`.
- Existing tests pass via `scripts/post-merge.sh`.

## Out of scope
- Any change to the canonical exporter `replit_integrations/export_graph_metadata.py` (it is already correct and is the reference of truth).
- Re-running a live ArangoDB migration to rewrite existing edges/properties (data migration is a separate concern unless explicitly requested).
- Semantic-layer (Perspective/Intent/Concept bridge) modeling — unaffected.

## Steps
1. **Frontend predicate fix** — In the mockup-sandbox triple builder and define-relationship components, remove `FOREIGN_KEY` as a predicate/edge type and replace the FK relationship with the `references` edge (child column → parent column). Re-point the self-loop guard at the correct predicate. Update the corresponding frontend test mocks to use `references` instead of `FOREIGN_KEY`.
2. **ArangoFixtures alignment** — Update the Arango fixture/verification/demo/test scripts so the FK flag is read as a `foreign_key` boolean on the column node (retiring `is_foreign_key` on edges), and child→parent links are traversed via `references` edges. Mirror the canonical edge shape (structural family, `references_table`/`references_column`).
3. **Planning doc fix** — Remove `FOREIGN_KEY` from the structural-edge-type list in `plan-012-dual-layer-delineation.yaml`, replacing/annotating with the `foreign_key` node attribute + `references` edge model.
4. **Solder catalog test** — Extend the catalog test so FK topology is validated through `references` edges, not just `contains`.
5. **Doc typo** — Correct the `references` edge example in `graph_metadata_canonical_example.md` (line ~99) where `edge_family` reads `system`; it should be `structural` to match the `_key` and the exporter.
6. **Verify** — Run `scripts/post-merge.sh`; ensure grep gates and all test files pass.

## Relevant files
- `replit_integrations/export_graph_metadata.py:387-463`
- `replit_integrations/graph_metadata_canonical_example.md:88-104`
- `replit_integrations/graph_metadata_canonical_example.json`
- `artifacts/mockup-sandbox/src/components/mockups/graph-triple/GraphTriple.tsx:7,31`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx:47,111,521-522,1066`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.history.test.ts:121,131`
- `hf-space-inventory-sqlgen/plans/plan-012-dual-layer-delineation.yaml:20`
- `Utilities/ArangoFixtures/verify_load_and_naming.py:210-211`
- `Utilities/ArangoFixtures/test_roundtrip_sqlite_to_graph.py:43,50,60`
- `Utilities/ArangoFixtures/demo_forward_backward_aql.py:28,39,49`
- `Utilities/ArangoFixtures/test_atomic_traversal.py:26,39,49,130,136,174-179`
- `hf-space-inventory-sqlgen/tests/test_solder_graph_catalog.py:122`
