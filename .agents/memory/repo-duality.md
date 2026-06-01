---
name: Public vs private repo duality
description: Why this public repo mirrors the private Windows/SQL Server repo in structure even though environments differ
---

## Rule
This public repo is a prototype sandbox that intentionally mirrors the structure of the private Windows/SQL Server repo. Scripts, config files, and CI steps that exist here may not run "live" — they exist to prove out patterns that get ported to the private repo.

**Examples:**
- `dab_config.json` — prototype reference artifact with CRM demo entities. Private repo has a real DAB (Data API Builder) service on Windows/SQL Server.
- `sync_db_to_dab_config.py` — works correctly as a script; CI only runs it in `--dry-run` mode here (no live write, no auto-commit), because there is no real DAB target.
- The public repo uses SQLite + Python/Linux; the private repo uses SQL Server + Windows.

**Why:** The user needs structural parity so patterns developed here can be directly transferred to the private repo. The repos are deliberately kept similar in file/script/workflow layout.

**How to apply:** When adding a new script or CI step, keep it in this repo even if it won't run live. Run it as `--dry-run` in CI if it would write to an external system that doesn't exist here. Never remove scaffolding just because the live target isn't present.
