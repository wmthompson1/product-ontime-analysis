# Port SQLMesh orchestrator & masking models

## What & Why
Bring the company's private-repo SQLMesh work into this repo: the
`orchestrator_handshake.py` script (which routes a natural-language intent to a
physical column through the masking pipeline) plus the `raw_user_def_fields` and
`raw_matrix_driven` SQLMesh models. This lets the orchestrator route semantic
requests through SQLMesh models to masked physical data, on top of the existing
`Utilities/SQLMesh` project.

## Source files (provided)
The user has provided the source files in `attached_assets/`. These reflect the
company's private repo and may lag this repo's current structure — treat them as a
reference to reconcile, not files to copy verbatim:
- `attached_assets/orchestrator_handshake_1781296696668.py`
- `attached_assets/raw_user_def_fields_1781296732328.py`
- `attached_assets/raw_matrix_driven_1781296761547.py`

## Done looks like
- `orchestrator_handshake.py` lives in this repo and runs end-to-end
  non-interactively, reporting its environment + semantic validation phases as passing.
- The `raw_user_def_fields` and `raw_matrix_driven` models exist in the SQLMesh
  project and render/plan successfully against the duckdb gateway.
- The orchestrator resolves a sample intent (e.g. "Legacy Manufacturer Code") to its
  physical column (USER_DEF_1) and returns masked staging data through the models.

## Out of scope
- The Python 3.13 runtime upgrade (separate prerequisite task).
- Production scheduling / deployment of SQLMesh.
- Reworking the existing masking_matrix pipeline beyond what these models require.
- LLM-generated SQL — routing must stay on SME-approved / masked outputs (Solder Pattern).

## Steps
1. Add the provided `orchestrator_handshake.py` at an agreed location and fix its paths
   to match this repo. Note: the source points at `hf-space-inventory-sqlgen/manufacturing.db`,
   but the real DB lives at `hf-space-inventory-sqlgen/app_schema/manufacturing.db`.
2. Port the `masking_helpers` module first. Both provided models import from
   `Utilities.SQLMesh.models.raw.masking_helpers` (`_load_active_cert`, `resolve_cert_dir`,
   `load_masking_matrix`, `load_masking_types`, `get_masking_rules_for_table`,
   `apply_masking_to_df`), and it does not exist yet — without it the models won't import.
   Reuse this repo's existing masking_matrix logic where it already covers these.
3. Add the `raw_user_def_fields` and `raw_matrix_driven` models into the existing
   SQLMesh model tree (`Utilities/SQLMesh/models/raw`), matching the established
   raw/staging naming and the duckdb dialect/config.
4. Wire the semantic intent -> physical column mapping to read from manufacturing.db
   metadata and the masking matrix. The source uses a hardcoded `semantic_map` dict
   (and a dead `sqlite_master` query) for "Legacy Manufacturer Code" -> USER_DEF_1 —
   replace that with a real lookup against this repo's schema metadata.
5. Run the orchestrator handshake non-interactively and confirm both phases pass;
   render/validate the new models with SQLMesh.
6. Add a short README note for the orchestrator and, if appropriate, mirror the
   existing SQLMesh CI workflow for the new models.

## Version reconciliation notes
The provided files lag this repo's structure. Reconcile (don't copy verbatim):
- `masking_helpers` dependency is missing — must be ported/created (see step 2).
- DB path drift: `app_schema/manufacturing.db` is the real location (see step 1).
- Semantic mapping is hardcoded in the source — replace with metadata-driven lookup
  (see step 4).
- The handshake validates `Utilities/SQLMesh/analysis` exists — it does, so that check
  passes as-is.

## Architectural constraints
- Routing must only ever return SME-approved / masked output (Solder Pattern) — never
  LLM-generated SQL.
- Run handshake non-interactively (the company's repo hit a hang from a SQLMesh
  context fixture / interactive plan prompt — guard against that here).

## Relevant files
- `attached_assets/orchestrator_handshake_1781296696668.py`
- `attached_assets/raw_user_def_fields_1781296732328.py`
- `attached_assets/raw_matrix_driven_1781296761547.py`
- `Utilities/SQLMesh/config.yaml`
- `Utilities/SQLMesh/models/raw`
- `Utilities/SQLMesh/models/staging`
- `Utilities/SQLMesh/requirements.txt`
- `Utilities/SQLMesh/scripts/normalize_models.py`
- `ddl/dbo.USER_DEF_FIELDS.sql`
- `.github/workflows/sqlmesh.yml`
- `masking_matrix.csv`
- `masking_matrix.py`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
