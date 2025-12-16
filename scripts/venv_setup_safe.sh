#!/usr/bin/env bash
set -euo pipefail

# Prevent being sourced: if BASH_SOURCE != $0 then script is sourced
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  echo "This script must be executed, not sourced. Run: bash ${BASH_SOURCE[0]}"
  return 0 2>/dev/null || exit 0
fi

# Idempotent venv setup for the repo
# Usage: ./scripts/venv_setup_safe.sh [PYTHON_EXECUTABLE] [VENV_DIR] [REQ_FILE]

PY="${1:-python3}"
VENV_DIR="${2:-.venv}"
REQ_FILE="${3:-mcp_server/requirements.txt}"

echo "Using Python: ${PY}"
echo "Creating venv in: ${VENV_DIR} (if missing)"

if ! command -v "${PY}" >/dev/null 2>&1; then
  echo "Error: python executable '${PY}' not found in PATH. Provide a full path or install Python." >&2
  exit 2
fi

if [ ! -d "${VENV_DIR}" ]; then
  "${PY}" -m venv "${VENV_DIR}"
  echo "Created venv at ${VENV_DIR}"
else
  echo "Virtualenv already exists at ${VENV_DIR}"
fi

echo "Upgrading pip/setuptools/wheel within venv..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

if [ -f "${REQ_FILE}" ]; then
  echo "Installing requirements from ${REQ_FILE} into venv..."
  "${VENV_DIR}/bin/pip" install -r "${REQ_FILE}"
else
  echo "Warning: requirements file '${REQ_FILE}' not found. Skipping."
fi

echo "Installing lightweight test utilities (pytest, httpx) into venv..."
"${VENV_DIR}/bin/pip" install -U pytest httpx

echo
echo "Done. To activate the venv in this shell, run:"
echo "  source ${VENV_DIR}/bin/activate"
echo "To run python/pip without activating, use:"
echo "  ${VENV_DIR}/bin/python --version"
echo "  ${VENV_DIR}/bin/pip freeze | sed -n '1,200p'"