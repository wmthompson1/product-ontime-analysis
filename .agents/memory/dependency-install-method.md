---
name: Dependency install method (uv pip, not uv sync)
description: How to (re)install this repo's Python deps and why uv.lock must not be trusted.
---

Install Python deps from the requirements manifests with `uv pip install`, never `uv sync` / `installLanguagePackages`.

**Why:** `uv.lock` in this repo is stale — `uv sync` prunes the environment down to only the handful of `[project].dependencies` in `pyproject.toml` (~10 pkgs), wiping the real working set (gradio, fastapi, sqlglot, torch, langchain, sqlmesh, chromadb, ...). The actual dependency set lives in `requirements.txt` + `hf-space-inventory-sqlgen/requirements.txt`, NOT in pyproject/uv.lock.

**How to apply:**
- Rebuild env: `uv venv .pythonlibs --python <interpreter>` then `uv pip install --python .pythonlibs/bin/python -r requirements.txt -r hf-space-inventory-sqlgen/requirements.txt`.
- `scripts/post-merge.sh` already installs this way (its install lines use `uv pip install`).
- The full set is large (~539 pkgs incl. a multi-GB torch CUDA build). Run installs in the FOREGROUND so they reuse the uv cache (`/home/runner/workspace/.cache/uv`) and resume across command timeouts; detached/background installs tend to get OOM-killed.
- `faiss`, `sdv`, `sdmetrics` are NOT in any manifest and imported nowhere — they were orphan installs in older envs. Their absence is not a regression; do not reinstall to "restore parity".
