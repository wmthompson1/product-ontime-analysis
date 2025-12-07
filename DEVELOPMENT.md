# Development (Docker-free)

This repository primarily contains Python code. The devcontainer (Docker) configuration has been removed in favor of a lightweight, Docker-free local workflow.

Quick setup

- Install `nvm` (Node Version Manager) and use Node 18 as pinned in `.nvmrc`:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
# restart your shell, then:
nvm install
nvm use
```

- Install Node dependencies (if/when you add JS packages):

```bash
npm install
```

Python environment

- Create a venv and install Python deps:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt   # if present
```

NPM helpers

- The repo includes a minimal `package.json` with helper scripts:
  - `npm run venv:create` — create Python virtualenv (`.venv`).
  - `npm run venv:install` — activate the venv and run `pip install -r requirements.txt` (best run from an interactive shell).
  - `npm run start:python` — runs `python3 ./001_Entry_Point_Kane_Ragas.py` (adjust to your preferred entrypoint).

NPM scripts (root `package.json`)

This repo includes a more comprehensive `package.json` at the repository root to help run the main components without Docker. Useful scripts:

- `npm run venv:create` — create a Python venv at `.venv`.
- `npm run venv:install` — activate `.venv` and install `requirements.txt` (interactive shell recommended).
- `npm run dev:astro` — run the Astro frontend locally: `cd astro-sample && npm install && npm run dev`.
- `npm run dev:flask` — installs Python deps (via `venv:install`) and runs the Flask backend: `python main.py`.
- `npm run dev:hf` — runs the HF Space app in `hf-space-inventory-sqlgen` (creates venv there, installs deps, runs `app.py`).
- `npm run dev:all` — runs `dev:astro`, `dev:flask`, and `dev:hf` in parallel using `concurrently` (devDependency). This is convenient for local full-stack dev.

Examples

```bash
# start Astro only
npm run dev:astro

# start Flask only (after creating .venv once)
npm run dev:flask

# start all components in parallel
npm run dev:all
```

Why this approach

- Simpler for a single user: no Docker images to build or manage.
- Use native tools (`nvm`, `venv`, `pip`, `npm`) for fast iteration.
- Commit lockfiles (e.g. `package-lock.json`, `requirements.txt`) to preserve reproducible installs.

If you later want to re-add a devcontainer, create a `.devcontainer/` directory with a `devcontainer.json` and `Dockerfile`.

Components — Local setup

Below are the main components and how to run them locally (Docker-free):

- **Astro Frontend:**
  - `cd astro-sample && npm install && npm run dev`
- **Flask Backend:**
  - `pip install -r requirements.txt && python main.py`
- **HF Space:**
  - `cd hf-space-inventory-sqlgen && pip install -r requirements.txt && python app.py`
- **Database:**
  - Use a local PostgreSQL instance or a cloud provider (Neon, Supabase, etc.) and configure connection strings in your app's config or environment variables.

If you'd like, I can add helper scripts to `package.json` to run these components from the repo root.
