# Arango env migration and CI persister

This repository migrated Arango environment variables from `DATABASE_*` to explicit `ARANGO_*` names.

Files added by this change:

- `.github/workflows/persist-on-schema-change.yml` — GitHub Actions workflow that runs the persister when files under `data/`, `schema/` or `scripts/persist_to_arango.py` change.
- `scripts/ci_persist.sh` — small CI wrapper to call the persister.

How the workflow runs

- The workflow is triggered on push when schema or GraphML/data files change. It requires repository secrets to be set:
  - `ARANGO_URL`
  - `ARANGO_USER`
  - `ARANGO_PASSWORD`
  - `ARANGO_DB`

Set those secrets in GitHub (Settings → Secrets) before enabling the workflow.

Alternative scheduling

- If you want a scheduled run instead of on push, edit the `on:` section of the workflow to add a `schedule:` cron entry.

Running locally

- To run the persister locally, make sure `ARANGO_*` environment variables are available (or keep the `DATABASE_*` compatibility variables in your environment) and run:

```bash
set -a && source .env && set +a
.venv/bin/python3 scripts/persist_to_arango.py || python3 scripts/persist_to_arango.py
```
