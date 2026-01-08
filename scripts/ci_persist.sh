#!/usr/bin/env bash
set -euo pipefail

# CI wrapper to run the persister. Expects ARANGO_* env vars to be set from secrets.
echo "Running Arango persister in CI..."
echo "ARANGO_URL=${ARANGO_URL:-}", "ARANGO_DB=${ARANGO_DB:-}"

# Print python version
python -V || true

# If there's a virtualenv or dependencies, rely on system python in CI
python3 scripts/persist_to_arango.py

echo "Persister finished."
