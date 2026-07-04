# Deprecate Legacy Perspective Graph Paths (pod19-aligned)

## What & Why
Per pod19 (`pods/pod19.md`), the semantic graph today carries `perspective` (and `category`) redundantly: as a standalone `perspectives` vertex collection with `operates_within` (Intent→Perspective) and `uses_definition` (Perspective→Concept) edges in ArangoDB, **and** as a string property on `bindings` documents. The "Dovetailed Edge-Property Model" collapses the triangular join into a single edge with `perspective` and `category` as **edge attribute properties**, eliminating vertex bloat and naturally complementing the deterministic 5-segment edge-key formula already implemented in the mockup.

`Category` is **not** an Arango vertex in this codebase — it lives as a property in `reviewer_manifest.json`, `app_schema/queries/index.json`, and the `CATEGORY_MAP` constant in `app.py`. Pod19 confirms it should join `perspective` as an edge attribute property.

`defined_by` mentioned in the prior plan-mode screenshot does **not** exist in this repo — audited and confirmed. The real legacy surfaces are `perspectives` (vertex), `operates_within` (edge), `uses_definition` (edge).

## Done looks like
- The Arango `manufacturing_graph` no longer contains the `perspectives` vertex collection, nor the `operates_within` / `uses_definition` edge collections.
- A single `Column_Bindings` edge collection carries the dovetailed properties — `{ perspective, category, discriminator_clause }` — on every edge (with `_from`/`_to` pointing directly between the source and target without a perspective hop in between). The existing `bound_to` edges are the right starting point for this reshape; whether they get renamed to `Column_Bindings` is a tactical decision during step 4.
- `(Intent, Field) → Concept` resolution in `semantic_reasoning.py` returns identical results to today, sourced from the edge-property lookup on `Column_Bindings` (no traversal through a Perspective vertex).
- `solder_engine.py`'s perspective-based binding selection produces byte-equal SQL output (already reads `.perspective` as a string property — confirm and lock with a regression test).
- `graph_sync.py` no longer writes the deprecated vertex or edges; running it against a fresh Arango produces only the dovetailed shape.
- `app.py` MCP endpoints (`/mcp/tools/get_perspectives`, `/mcp/tools/resolve_field_for_perspective`, `/mcp/tools/get_perspective_concepts`) continue to work — they read from SQLite, which is unchanged.
- A one-shot Arango cleanup migration script drops the three legacy collections, gated by a pre-flight that refuses to run if any reader still references them.
- A `_unitTest`-tagged regression suite asserts `edge_payload["properties"]["perspective"]` and `edge_payload["properties"]["category"]` exist on every committed edge, mirroring `scripts/test_load_erp_ddl_into_sqlite.py` patterns.

## Out of scope
- Changing the SQLite source-of-truth tables (`schema_perspectives`, `schema_intent_perspectives`, `schema_perspective_concepts`) — these remain as the relational source and feed the bridge-row properties.
- Changing the Gradio UI shape — Perspective and Category continue to be selectable in the UI.
- Modifying the `DefineRelationship.tsx` mockup beyond what's needed to match the final edge-property shape (it already shows the right structure).
- Any change to `reviewer_manifest.json` schema or the Binding Resolver pattern.
- **Open question A (Component_Fields / HAS_COLUMN)**: pod19's alignment table asserts "`HAS_COLUMN` stays at exactly zero across sync passes" — but the current `atomic_column` vertex collection contains 251 column nodes with 251 `HAS_COLUMN` edges, intentionally built and DDL-round-trip-validated (per `replit.md`). This is a much larger refactor (deletes the entire Atomic Solder layer). **Excluding it from this task pending user decision** — see Open Questions below.

## Open questions before execution
1. **Edge-key segment ordering**: Pod19 example shows `WOR_PAR_001_PAR_Engineering` → `{LLL}_{RRR}_{NNN}_{XXX}_{Perspective}` (counter before intent prefix). The mockup currently implements `{LLL}_{RRR}_{XXX}_{NNN}_{Perspective}` (intent prefix before counter) — locked in last session per the user's pick (b). **Which is canonical?** If pod19 wins, the mockup's `assembleEdgeId()` helper needs a one-line swap and the screenshots in this session are outdated.
2. **Component_Fields / HAS_COLUMN deprecation**: Pod19 table row 3 asserts `HAS_COLUMN` should stay at zero — directly contradicting the 251-edge Atomic Solder layer just built. **In or out of this task's scope?** Treating as out-of-scope unless told otherwise; if in scope, this becomes a much larger second task #1b.

## Steps
1. **Consumer-audit lockdown + grep gate** — Confirm the audit is complete and freeze the list of legacy readers before any writer changes. Add a CI grep gate that fails on any new reference to `operates_within`, `uses_definition`, or the `perspectives` vertex collection. Confirm `defined_by` truly does not exist anywhere and document that finding.
2. **Migrate `semantic_reasoning.py` readers to edge properties** — Replace the AQL traversal `Intent --operates_within→ Perspective --uses_definition→ Concept` with a direct edge-property lookup keyed by `(perspective, intent)` and `(perspective, concept)` on the dovetailed edge collection. Keep all public function signatures identical. Add pin-current-behavior unit tests with fixture data before the swap, then run them after to assert byte-equal output.
3. **Verify `solder_engine.py` already reads perspective as a property** — Audit confirmed `find_binding_for_concept` filters on `binding.perspective` (string field), not graph traversal. Add a regression test asserting identical SQL output for a fixed set of `(intent, concept, perspective)` tuples; no code change expected, but lock the behavior.
4. **Stop the writers in `graph_sync.py` and emit dovetailed edges** — Remove the code paths that create the `perspectives` vertex and the `operates_within` / `uses_definition` edges. Reshape the remaining edge writer (likely the existing `bound_to`, possibly renamed to `Column_Bindings` per pod19) to emit `properties: { perspective, category, discriminator_clause }` on every edge. Keep the SQLite read side untouched.
5. **`_unitTest`-tagged regression suite** — Add `test_binding_edge_properties_unitTest()` following pod19's template and `scripts/test_load_erp_ddl_into_sqlite.py` patterns. Assert every committed edge has `properties.perspective` and `properties.category`. Run the suite green before proceeding to step 6.
6. **Arango cleanup migration** — Write `hf-space-inventory-sqlgen/migrations/drop_legacy_perspective_graph.py` that drops `perspectives`, `operates_within`, `uses_definition` from `manufacturing_graph`. Include a pre-flight guard that refuses to run if the grep gate from step 1 finds any remaining reader. Make it idempotent.
7. **Post-migration validation** — Run `verify_graph.py` plus the new regression tests to assert: (a) the three legacy collections are gone, (b) `semantic_reasoning` and `solder_engine` produce byte-equal SQL output vs. the pre-migration baseline, (c) the MCP `/mcp/tools/get_perspectives` endpoint still returns the expected list (sourced from SQLite, unaffected).
8. **Sync mockup constants and `replit.md` architecture notes** — If the mockup `DefineRelationship.tsx` needs a static-data constants file (per pod19's `MOCK_BINDING_EDGES` template), introduce it. Update `replit.md` to replace the three-hop traversal description with the dovetailed edge-property model so future agents don't re-introduce it.

## Architectural constraints
- **Source-of-truth ordering**: SQLite (`schema_perspectives`, etc.) → graph_sync writers → Arango dovetailed edges → readers. Never let readers go around the edge property to re-hydrate a Perspective vertex.
- **Migration order is non-negotiable**: readers must be moved off the legacy edges *before* the writers stop emitting them, and the Arango drop migration runs *last*. Skipping order risks live-graph reads failing mid-deploy.
- **No SQL output drift**: any change to `semantic_reasoning` or `solder_engine` must produce byte-equal SQL for fixed inputs. The whole point of the Solder Pattern is determinism — a refactor cannot regress this.
- **Pod19 is the canonical edge shape**: `properties: { perspective, category, discriminator_clause }` is the contract. Any divergence from this in graph_sync.py is a bug in this task.
- **Mockup ↔ graph parity**: the `DefineRelationship.tsx` Live Identity Preview strip's identity keys must match what the actual Arango edges expose. The segment-ordering open question must be resolved before step 4.

## Relevant files
- `pods/pod19.md`
- `hf-space-inventory-sqlgen/graph_sync.py:32-54,151-155,198-214,290-329,384-450`
- `hf-space-inventory-sqlgen/semantic_reasoning.py:15-18,93,274,329,379,493-494,537,602`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app.py:1352-1391,1626,1690-1702,1992,2013,2031,2424,2726,2736`
- `hf-space-inventory-sqlgen/verify_graph.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql:410-432`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`
- `scripts/test_load_erp_ddl_into_sqlite.py`
- `replit.md`
