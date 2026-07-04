---
title: Confirm the environment-variable commit guard actually blocks writes when unset
---
# Confirm the environment-variable commit guard actually blocks writes when unset

  ## What & Why
  The committer's docstring states that live writes also require `MRP_ENABLE_GRAPH_COMMIT=true` in the environment. The new mock tests confirm `_do_commit` is called when `commit=True`, but nothing verifies what happens inside `_do_commit` (via `mrp_terminology_stager.commit_payload`) when the env var is absent or set to a falsy value. A missing test here means a developer could remove or weaken the guard without any CI signal.

  ## Done looks like
  - A test that calls `_do_commit` (or the full `run(commit=True)` path without mocking _do_commit) with `MRP_ENABLE_GRAPH_COMMIT` absent or set to `"false"` and asserts it raises or returns a refused/no-op result rather than writing
  - The test should cover at least: env var absent, env var = "false", env var = "0"

  ## Relevant files
  - `scripts/mrp_approval_committer.py` — `_do_commit`, docstring
  - `scripts/mrp_terminology_stager.py` — `commit_payload` (where the guard likely lives)
  - `tests/test_mrp_approval_committer.py`