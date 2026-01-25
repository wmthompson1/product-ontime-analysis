## SQLMesh Cache & Cleanup

This document explains how to safely clean up SQLMesh state and the local file-system cache used during development and CI runs. The `sqlmesh destroy` CLI command removes SQLMesh state tables and file-system cache entries and is useful when you want to start from a clean slate.

**Warning:** `sqlmesh destroy` is destructive — it will remove SQLMesh-managed state (snapshots, intervals, schedules stored in the configured state sync database) and clear local cache files. Back up any important files or database state before running it in production-like environments.

---

**What `sqlmesh destroy` does**

- Drops SQLMesh state tables from the configured state backend (by default the project state DB configured in `config.yaml`).
- Removes SQLMesh file-system cache (local artifacts, compiled snapshots, temporary files). Depending on your configuration, this may include files under `.sqlmesh/` or the configured cache directory.
- Leaves user data (for example your seed CSVs in `seeds/` or external `raw.*` tables) untouched.

Use `sqlmesh destroy` when you need to:
- Reset local development state before a fresh `plan`/`apply` run.
- Recover from corrupted state or incompatible migrations in the state DB.
- Force CI to evaluate the project with an empty state snapshot table set.

---

How to run

1. Open a terminal in your SQLMesh project directory (the folder with `config.yaml`) — for this repository, `Utilities/SQLMesh`.

2. Optionally back up your state DB or local cache. Example: copy the DuckDB file or take a DB dump.

3. Run the destroy command:

```bash
cd Utilities/SQLMesh
sqlmesh destroy --yes
```

Notes:
- `--yes` or `--no-prompts` is recommended in CI or scripted runs to avoid interactive confirmation.
- If your project uses a remote state backend (e.g., Postgres or other DB), ensure your credentials and environment variables are correct and that you want the state tables removed.

Rebuilding state and cache

After a destroy, recreate state via `sqlmesh plan` and `sqlmesh apply` (or `sqlmesh plan --auto-apply`):

```bash
sqlmesh plan --no-prompts --auto-apply
```

This will recreate the state tables and repopulate any cache entries required by the evaluator. If you removed the local DuckDB (`db.db`) file, ensure you have any required `raw.*` seeds available so staging models can be evaluated.

CI considerations

- In CI, prefer running `sqlmesh destroy --no-prompts` early in the job if you want a guaranteed clean state for the project evaluation. Example job step:

```yaml
- name: Clean SQLMesh state
  run: |
    cd Utilities/SQLMesh
    sqlmesh destroy --no-prompts || true
```

- Follow with loading seed CSVs (if your models depend on `raw.*` tables) and then run `sqlmesh plan`.

Safety and backups

- Back up your state DB before destroying it if you may want to restore history or execution intervals.
- For DuckDB local development, copy the DB file (e.g., `cp db.db db.db.bak`) before running `destroy`.

Troubleshooting

- If `sqlmesh destroy` fails due to DB permissions, check environment variables and DB credentials.
- If state was removed but CI still reports stale cache, manually remove the `.sqlmesh/` or cache directory referenced by your SQLMesh config.
- If you see schema/migration errors after restoring a DB, run migrations or recreate state from scratch by destroying and planning again.

Related commands

- `sqlmesh info` — show project info and current environment state.
- `sqlmesh plan` / `sqlmesh apply` — rebuild state and materialize snapshots after cleaning.
- `sqlmesh test` — run model tests; useful after a clean run to validate behavior.

---

Local cleanup steps
-------------------

1. To fully clear SQLMesh local state run:

  ```bash
  cd Utilities/SQLMesh
  sqlmesh destroy --no-prompts --all
  ```

2. Remove any leftover local warehouse/db files (for example the project's DuckDB `db.db`).

3. In CI, add an early step to run `sqlmesh destroy --no-prompts` and then load seeds before `sqlmesh plan`.

If you’d like, I can add a CI job snippet to `/.github/workflows/sqlmesh.yml` that runs `sqlmesh destroy --no-prompts` at the start of the job and then loads seed CSVs into the local DuckDB before `sqlmesh plan`. Want me to add that?

## Use Case - Missing field 
does this error warrant reloading the cache? --

Short answer: no — not immediately. That BinderError means the column capa_id does not exist in the table you queried, not that DuckDB's cache is stale. Verify the table/schema first and only reload/recreate the table or clear SQLMesh state if those checks show a problem.
