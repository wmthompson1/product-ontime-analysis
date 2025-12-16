#!/usr/bin/env bash
set -euo pipefail

# Start an interactive shell with the repo venv activated.
# Usage: ./scripts/open_activated_shell.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Ensure venv exists and write VS Code settings that enable auto-activation
./scripts/venv_setup.sh python3 .venv true

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  echo "Launching interactive bash with venv activated..."
  exec bash --rcfile "$REPO_ROOT/.vscode/activate_rc"
else
  echo "No venv found at .venv; activated shell cannot be started." >&2
  exec bash
fi
