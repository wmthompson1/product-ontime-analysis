---
title: Upgrade project to Python 3.13
---
# Upgrade project to Python 3.13

## What & Why
Company policy requires Python newer than 3.11, and the SQLMesh / SQLGlot AST work
needs 3.13 (3.14 breaks SQLGlot AST compatibility). Move the Replit project runtime
from Python 3.11 to 3.13 and make sure every existing app and test still runs.

## Done looks like
- The environment reports Python 3.13.x.
- The "HF Space Inventory SQL" app starts and the Gradio UI loads and serves.
- The "Flask App" workflow starts cleanly.
- All dependencies install successfully on 3.13.
- The full test/parity gate passes.

## Out of scope
- Porting the SQLMesh orchestrator and models (handled in the dependent task).
- Going beyond 3.13 (3.14 broke SQLGlot AST handling in the company's other repo).
- Any feature/behavior changes — this is purely a runtime move + verification.

## Steps
1. Switch the project's Python runtime module from 3.11 to 3.13 and update the
   minimum-version pin in the project metadata to match.
2. Reinstall all dependencies under 3.13 and resolve any package that lacks a 3.13
   wheel, paying special attention to the ML-heavy set (torch / sentence-transformers,
   chromadb, datasets, scipy, faiss, langchain stack).
3. Restart all workflows and confirm the HF Space app and Flask app start with no
   import or runtime errors.
4. Run the full test/parity gate and fix any 3.13-specific breakage.
5. Record the 3.13 runtime baseline in the project README notes.

## Architectural constraints
- Pin to Python 3.13 specifically — do NOT move to 3.14 (it breaks SQLGlot AST
  compatibility the SQLMesh work depends on).

## Relevant files
- `.replit`
- `pyproject.toml`
- `requirements.txt`
- `scripts/post-merge.sh`
- `hf-space-inventory-sqlgen/app.py`
- `Utilities/SQLMesh/requirements.txt`
- `replit.md`