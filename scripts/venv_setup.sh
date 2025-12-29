#!/usr/bin/env bash
set -euo pipefail

# Prevent being sourced: if BASH_SOURCE != $0 then script is sourced
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  echo "This script must be executed, not sourced. Run: bash \"${BASH_SOURCE[0]}\"" >&2
  # If sourced, return non-zero; if executed, exit non-zero.
  return 1 2>/dev/null || exit 1
fi

# Idempotent venv setup for the repo
# Usage: ./scripts/venv_setup.sh [PYTHON_EXECUTABLE]

PY=${1:-python3}
VENV_DIR=${2:-.venv}
# pass a third arg (true) to write .vscode/settings.json enabling auto-activation
# Usage: ./scripts/venv_setup.sh [PYTHON_EXECUTABLE] [VENV_DIR] [write-vscode]
WRITE_VSCODE=${3:-false}
REQ_FILE="mcp_server/requirements.txt"

echo "Creating venv in $VENV_DIR using $PY (if it doesn't exist)"
if [ ! -d "$VENV_DIR" ]; then
  $PY -m venv "$VENV_DIR"
fi

echo "Upgrading pip/setuptools/wheel"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

if [ -f "$REQ_FILE" ]; then
  echo "Installing requirements from $REQ_FILE"
  "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
else
  echo "Warning: $REQ_FILE not found. Skipping requirements install."
fi

echo "Installing test utilities (pytest, httpx)"
"$VENV_DIR/bin/pip" install pytest httpx

echo "Done. To activate: source $VENV_DIR/bin/activate"

if [ "$WRITE_VSCODE" = "true" ]; then
  VSCODE_DIR=".vscode"
  SETTINGS_FILE="$VSCODE_DIR/settings.json"
  mkdir -p "$VSCODE_DIR"
  if [ -f "$SETTINGS_FILE" ]; then
    echo "Notice: $SETTINGS_FILE already exists; not overwriting. If you want to enable auto-activation, merge these settings into it:"
    echo '{"python.terminal.activateEnvironment": true, "terminal.integrated.inheritEnv": true}'
  else
    cat > "$SETTINGS_FILE" <<JSON
{
  "python.terminal.activateEnvironment": true,
  "terminal.integrated.inheritEnv": true
}
JSON
    echo "Wrote $SETTINGS_FILE to enable automatic venv activation in VS Code terminals."
  fi
fi
