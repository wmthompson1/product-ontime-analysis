#!/usr/bin/env bash
# One-command demo: prove the virtual SPARQL graph matches the SQL semantic layer.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure the toolchain is present (idempotent download).
if [ ! -x "${SCRIPT_DIR}/tools/ontop-cli-5.5.0/ontop" ]; then
  bash "${SCRIPT_DIR}/setup.sh"
fi

python3 "${SCRIPT_DIR}/parity_check.py"
