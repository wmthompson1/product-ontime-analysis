---
name: SQLMesh project gotchas
description: Non-obvious SQLMesh failure modes hit porting the orchestrator/raw models — helper serialization, empty python models, state/version migration, repo-root models.py shadow.
---

# SQLMesh project gotchas

## Project-local @model helper serialization
When a SQLMesh `@model` python file imports a helper from inside the project's
models tree (e.g. `models.raw.masking_helpers`), SQLMesh snapshots that helper
**by source** and recursively walks the module-level globals it references. Only
literals (`int/float/str/bytes/tuple/list/dict/set/bool`), modules, and callables
serialize. A module-global `pathlib.Path` or compiled `re.Pattern` raises
`SQLMesh cannot serialize ...` at load time (`sqlmesh info` / context load fails).

**Why:** the snapshot must be reconstructable in a fresh interpreter for
fingerprinting/state, so non-trivial live objects can't ride along.

**How to apply (project-local helpers used by python models):**
- Keep helper module globals as plain str/num, not `Path`/compiled regex. Store a
  path as a `str` and wrap in `Path(...)` *inside* the function; store a regex as
  its pattern `str` and compile/`re.match` inside the function.
- Helpers resolving a default path should take `path=None` and look up the default
  *inside* the call, not bind a `Path` at import time.
- Modules imported from *outside* the models tree (site-packages, app modules on
  `sys.path`) serialize as plain imports — fine.
- List project-local, non-model helper modules under `ignore_patterns` in
  `config.yaml` so the loader doesn't treat them as models.

**Module-level side effects are NOT captured.** The snapshot `python_env` keeps
only referenced names (imports/values/callables). An `import other_dir_module`
*survives* serialization, but the `sys.path.insert(...)` that made it importable
does **not**. So loading the project works (the helper's module-level bootstrap
runs in-process), yet EXECUTION from a reused snapshot (e.g. CI plan/run against
committed state) re-runs the bare `import` with no bootstrap and dies with
`ModuleNotFoundError`. Satisfy cross-directory imports needed at execution via
`PYTHONPATH` (or a lazy import inside a serialized function), never a load-time
`sys.path` hack alone. Concretely: models importing `masking_matrix` /
`masking_type` from `hf-space-inventory-sqlgen` need that dir on `PYTHONPATH` at
runtime (set it in CI), because the load-time bootstrap in `masking_helpers.py`
never reaches snapshot execution.

## Empty python models must be generators
A FULL python model that can legitimately produce zero rows must be a **generator**
(`def execute(...) -> Iterator[pd.DataFrame]:` using `yield df`, and a bare
`return` / `yield from ()` for the empty case). Returning an empty `pd.DataFrame`
fails *backfill* with: `Cannot construct source query from an empty DataFrame`.
This only bites at `plan`/`run` backfill time — `sqlmesh info` and `plan
--skip-backfill` won't catch it, so an empty-DataFrame model looks fine until
something actually executes it.

**How to apply:** a model reading from an external source that may be absent
(e.g. SQL Server via pyodbc in dev/CI) should `yield` rows when present and
`return` (empty generator) when the source can't be reached — while still letting
a real connection/query error propagate when the driver *is* present (fail loud in
prod, never silently mask).

## State/version migration coupling
SQLMesh state lives in the project's tracked DuckDB file (`Utilities/SQLMesh/db.db`,
~16MB, NOT gitignored) and records the SQLMesh version it was last migrated at. If
the installed/pinned SQLMesh is **ahead** of that state version, `sqlmesh plan`/`run`
abort: `SQLMesh (local) ... ahead of ... (remote). Please run a migration`.
`sqlmesh info`/`test` do *not* trip this check, so a mismatch hides until plan.

**How to apply:** when bumping `sqlmesh` in `Utilities/SQLMesh/requirements.txt`,
run `sqlmesh migrate` from the project dir and commit the updated `db.db`. CI runs
`sqlmesh migrate` before every plan/run as a safety net.

## Repo-root models.py shadow
Running a SQLMesh context from a script at the repo root puts the repo root on
`sys.path`, where an unrelated repo-root `models.py` shadows SQLMesh's project-local
`models/` package. Fix by removing the repo root from `sys.path` before loading the
context, or run from inside the project dir (CI does `cd Utilities/SQLMesh`).
