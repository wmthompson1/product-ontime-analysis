# Author & Harden MRP Set-Semantics Snippets

## What & Why
Once the set-criteria definitions for the 7 MRP concepts are SME-approved, this task implements them: it **repairs** the two naive approved snippets and **promotes** the five drafted-but-unapproved snippets so SolderEngine serves correct, set-aware SQL for all 7 concepts. This closes the Solder Pattern gap where these concepts either return naive SQL (ATP, AllocatedQuantity) or silently fail closed (the other five, whose files exist but are not in the manifest).

Depends on the set-criteria definition task — do not write or approve any snippet until those definitions are signed off.

## Done looks like
- ATP and AllocatedQuantity snippets are rewritten to match the approved set definitions (correct state conditions, scheduled-receipt/firm-supply handling, and time-phasing anchored to the data-derived AS_OF).
- SafetyStock, LeadTimeDemand, MinimumStockQuantity, MaximumStockQuantity, and EconomicOrderQuantity snippets are finalized to match their approved definitions and added to `reviewer_manifest.json` so SolderEngine serves them.
- Any Arango set-topology edges called for by the approved definitions are added via the canonical graph path (only if the definition requires them).
- `seed_elevations.py` bindings exist for every newly served concept.
- SolderEngine returns correct, set-aware SQL for all 7 concepts, and the SQL executes against `manufacturing.db` returning meaningful rows.
- `test_mrp_query_palette.py` is extended to assert the manifest/file/solder path for all 7 concepts.
- The full `scripts/post-merge.sh` gate passes (including any graph parity gates if edges changed).

## Out of scope
- Redefining the set semantics (that is the upstream definition task; this task implements the approved definitions).
- Adding new physical columns to the synthetic schema.
- Changes to concepts outside these 7.

## Steps
1. **Repair the two naive snippets** — Rewrite the ATP and AllocatedQuantity SQL to the approved set definitions and confirm they execute against `manufacturing.db`.
2. **Finalize the five drafts** — Bring the SafetyStock, LeadTimeDemand, MinimumStockQuantity, MaximumStockQuantity, and EconomicOrderQuantity snippets in line with their approved definitions.
3. **Add graph edges if required** — If any approved definition specifies set-topology edges, add them through the canonical graph path and re-run parity.
4. **Bind and approve** — Add `seed_elevations.py` bindings and promote all seven into `reviewer_manifest.json` so SolderEngine resolves each concept to its approved snippet.
5. **Test and gate** — Extend `test_mrp_query_palette.py` to cover all 7 concepts end-to-end and confirm the full post-merge suite passes.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/`
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
- `replit_integrations/seed_elevations.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `scripts/post-merge.sh`
