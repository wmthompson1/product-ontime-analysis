# Procurement Planning Interaction Trace

## What & Why
Author a procurement planning document whose core is an end-to-end **interaction trace** showing how a procurement question flows through the semantic layer: the SolderEngine (via the ProductionDispatcher) **determines user intent** and then **chooses the ontological mapping**, which resolves to SME-approved ground-truth SQL. This gives the aerospace-manufacturer / Berkeley Haas audience a concrete, defensible walkthrough of the "Solder Pattern" applied to procurement (reorder point, EOQ, safety stock, ATP), matching the three-pillar architecture diagram already on the canvas (ArangoDB + Ontop/SPARQL → SolderEngine → SQLGlot).

## Done looks like
- A new markdown document in `docs/` (e.g. `docs/procurement_planning.md`) that a non-engineer can read start to finish.
- It walks one concrete procurement question (e.g. "What do I need to reorder?") step-by-step through the pipeline:
  1. Natural-language question enters.
  2. **Intent determination** — closed-vocabulary intent classification (dispatcher) yields intent + concepts + perspective + confidence, never free-form SQL.
  3. **Ontological mapping selection** — how the chosen intent/concept resolves to a binding key: primary binding key vs. concept-path resolution, perspective filtering, elevate/suppress weights, and `resolves_to` edges (with the ArangoDB edge topology view).
  4. **Ground-truth SQL resolution** — binding key → `reviewer_manifest.json` → the physical approved `.sql` snippet (never generated).
  5. **Structural match / assembly** — SQLGlot parses the AST to confirm the physical tables/joins match (tables, not CTE structure), then transpiles to the target SQLite dialect.
- The trace is grounded in the real procurement (inventory) ground-truth views, not invented examples.
- A short section ties each stage back to the corresponding box in the canvas architecture diagram.
- Fail-closed behavior is called out: what happens when intent is ambiguous or no approved mapping exists (the engine refuses rather than hallucinating SQL).

## Out of scope
- No code changes to the engine, dispatcher, or graph — this is a documentation deliverable.
- No new ground-truth SQL snippets, graph nodes/edges, or schema changes.
- No changes to the canvas diagram (reference it only).
- Broader MRP netting/grid math beyond what's needed to frame the procurement question.

## Steps
1. **Pick the driving procurement scenario** — choose one concrete question anchored to an existing inventory ground-truth view (reorder point / EOQ / safety stock / ATP) and state the business goal in plain language.
2. **Document intent determination** — describe how the dispatcher classifies the question into a closed-vocabulary intent + concepts + perspective, and why generation is never used.
3. **Document ontological mapping selection** — explain primary-binding-key vs. concept-path resolution, perspective filtering, elevate/suppress weights, and the `resolves_to` edge lookup that binds the concept to physical columns; include the ArangoDB edge-topology angle.
4. **Document ground-truth SQL resolution** — show the binding key → `reviewer_manifest.json` → approved `.sql` file hop, emphasizing SME governance.
5. **Document the structural-match step** — explain SQLGlot AST parsing verifying physical tables/joins (tables, not CTEs) and dialect transpile to SQLite.
6. **Tie back to the architecture diagram and fail-closed behavior** — map each stage to its diagram box and describe what happens on ambiguity or a missing approved mapping.

## Relevant files
- `hf-space-inventory-sqlgen/production_dispatcher.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/semantic_reasoning.py`
- `hf-space-inventory-sqlgen/view_ontology_extractor.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_reorderpoint_20260703_000001.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_eoq_20260703_000010.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_safetystock_20260703_000006.sql`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_atp_20260703_000004.sql`
- `docs/mrp_set_semantics_criteria.md`
