#!/usr/bin/env bash
set -euo pipefail

# Idempotent venv setup for the repo
# Usage: ./scripts/venv_setup.sh [PYTHON_EXECUTABLE]

PY=${1:-python3}
VENV_DIR=${2:-.venv}
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
