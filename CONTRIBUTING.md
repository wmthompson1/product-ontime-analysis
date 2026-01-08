## Contributing - Setup & Tests

This project uses a local virtual environment (`.venv`) for running the MCP server and tests.

Prerequisite
- Python 3.10+ installed on your machine.

Quick start (recommended)

1. Create and populate the repository venv (idempotent):

```bash
./scripts/venv_setup.sh
```

2. Activate the venv for interactive use:

```bash
source .venv/bin/activate
```

3. Run the MCP server smoke helper (creates `.venv` if missing):

```bash
chmod +x scripts/run_smoke_locally.sh
./scripts/run_smoke_locally.sh 8000
```

4. Run the unit tests for the MCP server:

```bash
.venv/bin/python -m pytest -q mcp_server/tests
```

Editor integration
- VS Code users: the workspace recommends the `.venv` interpreter. See `.vscode/settings.json`.

Notes
- Keep `.venv/` out of version control (it's included in `.gitignore`).
- CI runs the same tests in an isolated environment via GitHub Actions.

Note: Space registration instructions and related files have been removed/archived — the previously-registered GitHub Space was deleted and any registration artifacts were moved to `archive/`.

If you encounter issues, please open an issue or contact the maintainers with logs and platform details.
