```markdown
# Clean start baseline

This branch is a minimal baseline intended to be used as a "clean start" for the repository.
It intentionally excludes ephemeral `.env` files.

Quick steps to create & open a PR from this baseline:

1. Ensure you're on the branch you want to use as the baseline:
   git checkout main
   git pull origin main
   git checkout -b clean-start

2. Save the baseline files into the repo root (the files under `.github/`, `scripts/`, `docker-compose.yml`, `config.py`, `README.md`, and `scripts/recreate_from_graph.py`).

3. Commit and push:
   git add .
   git commit -m "clean start: baseline files (CI, docker, arango scripts, config shim)"
   git push -u origin clean-start

4. Open a Pull Request from `clean-start` → `main` in GitHub. Review the "Files changed" tab carefully; this PR may remove files that are not present here.

Notes:
- No `.env` files are included; keep sensitive and local configuration in your local `.env` or secret manager.
- CI includes a check to fail if legacy `database_` env prefix occurrences are found (see `.github/workflows/check-arango-env.yml`).
- `scripts/arangobackup.sh` and `scripts/arangorecreate.sh` are safe by default (dry-run). Use `--apply` and `ALLOW_COLLECTION_DROP=true` explicitly to perform destructive actions.
- `scripts/recreate_from_graph.py` can rebuild the Arango collections from a normalized NetworkX pickle. Use `--dry-run` first.
```