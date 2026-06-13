---
name: SQLMesh Python model serialization
description: Why shared helpers imported by SQLMesh @model python files must keep their module-level globals serializable (no Path / compiled regex).
---

# SQLMesh Python model serialization

When a SQLMesh `@model` python file imports a helper function that lives **inside
the project's models tree** (a project-local module, e.g. `models.raw.masking_helpers`),
SQLMesh snapshots that helper **by source** and recursively walks the module-level
globals the helper references. Only a narrow set serializes: literals
(`int/float/str/bytes/tuple/list/dict/set/bool`), modules, and callables
(`type`, `FunctionType`). Anything else — notably a `pathlib.Path` object or a
compiled `re.Pattern` held as a module global — raises
`SQLMesh cannot serialize ...` at load time (`sqlmesh info` / context load fails).

**Why:** the snapshot must be reconstructable in a fresh interpreter for
fingerprinting/state, so non-trivial live objects can't ride along.

**How to apply (for project-local helpers used by python models):**
- Keep module globals that helpers touch as plain strings/numbers, not `Path` or
  compiled patterns. Store a path as a `str` (e.g. `_REPO_ROOT_STR`) and wrap it
  in `Path(...)` *inside* the function body. Store a regex as its pattern `str`
  and compile (or use `re.match(pattern, ...)`) inside the function.
- Helpers that resolve a default path should take `path=None` and look up the
  canonical default *inside* the call, not bind a `Path` at import time.
- Modules imported from **outside** the project models tree (site-packages like
  `pandas`, or app modules added to `sys.path`) serialize as plain imports and are
  fine — the by-source walk only applies to project-local helper source.
- List any project-local, non-model helper module under `ignore_patterns` in
  `config.yaml` so the loader doesn't try to treat it as a model.

**Repo-root `models.py` shadow:** running a SQLMesh context from a script at the
repo root puts the repo root on `sys.path`, where an unrelated `models.py` shadows
SQLMesh's project-local `models/` package. Fix by removing the repo root from
`sys.path` before loading the context, or run from inside the project dir (CI does
`cd Utilities/SQLMesh && sqlmesh ...`, so its `sys.path[0]` is the project dir and
there is no shadow).
