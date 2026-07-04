# Living-Manifest Structural Fingerprints

## What & Why
Today the Solder Engine's only governance gate is "is this binding key `APPROVED` in `reviewer_manifest.json`?" There is no check on *what a snippet actually does*, and no supported way for an SME to rewrite an approved snippet (rename CTEs, reorder joins, change windowing/bucketing) without it looking like a brand-new, ungoverned query.

This work elevates `reviewer_manifest.json` to a first-class, living part of the ontology and adds **structural fingerprint validation**: every approved snippet carries the *set of base tables* it touches (its fingerprint). The engine validates a snippet's structure — not its style — so SME rewrites are accepted as long as the base-table set is unchanged, and the system fails closed only when the manifest genuinely lacks a matching, structurally-valid entry. It also adds a **registration flow** so newly added SME snippets get fingerprinted and registered automatically, and wires the manifest's binding keys + base-table topology into the canonical semantic graph.

Core principle (unchanged): the engine NEVER generates, infers, or mutates SQL. It only reads, validates, and serves SME-approved snippets. SQL is treated as declarative (what), not procedural (how). Synthetic target dialect stays SQLite.

## Done looks like
- Every approved snippet in the manifest carries a structural fingerprint (its base-table set) that an SME can see and sign off on; all existing snippets are backfilled from their current `.sql` files.
- An SME can rewrite an approved snippet — rename/reorder CTEs, reorder joins, change windowing or bucket logic — and the Solder Engine still serves it, because the base-table set matches. The classic example holds: an ATP snippet keeps serving as long as its base tables are unchanged.
- The engine fails closed in exactly four cases and no others: (1) no binding key in the manifest, (2) no snippet file for that binding key, (3) no perspective-compatible snippet, (4) structural fingerprint validation fails (SQLGlot can't parse it, or the base-table set differs from the approved fingerprint). It never fails closed merely because the SQL is stylistically new.
- Adding a new SME snippet is a single supported action that extracts its fingerprint, assigns/uses a binding key, writes the manifest entry, and updates the perspective routing weights and concept-path edges — with no hand-editing and no SQL generation.
- The manifest's binding keys and their base-table topology are represented in the canonical semantic graph, and all existing graph parity and field-description coverage gates in `scripts/post-merge.sh` still pass.

## Out of scope
- Syncing the **live ArangoDB** graph (it is still on the legacy `concept_`-prefixed key model, so `sql_aql_parity` already fails independently of this change — pre-existing, unchanged here). All new graph work targets the canonical `sql_graph_*` tables + `graph_metadata.json` source of truth.
- Any LLM/AI generation, inference, or rewriting of SQL. No new snippet SQL is authored by the system.
- Changing the dispatcher's NL classification model or adding new business concepts/perspectives beyond what registering a snippet requires.
- Column-level or value-level validation. The fingerprint is the base-table set (plus join topology); it is deliberately style-agnostic.

## Steps
1. **Fingerprint model + backfill** — Define a structural fingerprint (the sorted set of base tables a snippet touches, plus its join/table topology) and add it to each manifest entry as an SME-visible, signed-off field. Backfill all existing approved snippets by extracting their base tables from the current `.sql` files using the existing SQLGlot-based extractor (CTE names excluded). Extraction must be deterministic and SQLite-dialect.
2. **Runtime structural validation in the engine** — In the snippet-serving path, after loading a snippet's SQL, extract its base-table set and compare it for equality against the stored fingerprint. Accept any snippet whose base-table set matches, regardless of CTE names, join order, or windowing/bucket logic. Reuse the engine's existing base-table extraction helper so runtime and backfill agree.
3. **Tighten the fail-closed boundary** — Make refusal happen in exactly the four documented cases (missing binding key, missing snippet, no perspective-compatible snippet, fingerprint validation failure) and audit the existing serving paths so no stylistic difference can trigger a refusal. Failures should return the engine's existing structured fail-closed report (not an uncaught crash), naming which of the four conditions tripped.
4. **New-snippet registration flow** — Provide one supported action (module/CLI) that takes a new SME `.sql` file plus its concept anchor and perspective, extracts the fingerprint, assigns or reuses a binding key via the existing key utility, writes the manifest entry (with SME sign-off/audit fields), and updates the perspective routing weights and concept-path edges. It must never generate or mutate SQL, and must be idempotent on re-run.
5. **Wire the manifest into the canonical graph** — Represent each binding key as a distinct graph node and its base-table set as topology edges, alongside the existing column/reference/resolves_to structure. Re-export the canonical graph with a bumped `SCHEMA_VERSION`. Critical constraint: binding-key nodes must be a distinct node type that is NOT counted as a column node, so the field-description coverage gate (currently 231/231 column nodes) stays exact; keep `graph_metadata.json` in lockstep with the `sql_graph_*` tables.
6. **Tests + gates** — Add tests covering: deterministic fingerprint extraction; accept-on-rewrite (renamed CTEs, reordered joins, changed windowing → same base tables → served); reject-on-table-change (added/removed base table → fail closed); parse-failure → fail closed; the exact four-condition boundary; registration round-trip (register → serve → validate); and graph parity + field-description coverage after the re-export. All of `scripts/post-merge.sh` must pass except the pre-existing live-ArangoDB `sql_aql_parity` (documented out of scope).

## Relevant files
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/view_ontology_extractor.py`
- `hf-space-inventory-sqlgen/binding_key_utils.py`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets`
- `replit_integrations/export_graph_metadata.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/field_description_coverage_check.py`
- `scripts/post-merge.sh`
