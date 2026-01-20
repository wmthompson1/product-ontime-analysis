#!/usr/bin/env bash
set -euo pipefail

# run_persist.sh
# Convenience wrapper to run the NCM elevation persistence step with safe
# defaults. Optionally starts a temporary ArangoDB Docker container for local
# testing.

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR"

START_DOCKER=false
if [[ "${1:-}" == "--start-docker" ]]; then
  START_DOCKER=true
fi

: "${DATABASE_HOST:=http://localhost:18529}"
: "${DATABASE_USERNAME:=root}"
# nx_arangodb treats an empty password as "not set" — provide a placeholder
: "${DATABASE_PASSWORD:=pass123}"
: "${DATABASE_NAME:=networkx_graphs}"

if $START_DOCKER; then
  echo "Starting temporary ArangoDB container (name: arango-run)..."
  docker rm -f arango-run >/dev/null 2>&1 || true
  docker run -d --name arango-run -p 18529:8529 -e ARANGO_NO_AUTH=1 arangodb/arangodb:3.10 >/dev/null
  echo "Waiting for ArangoDB to initialize..."
  sleep 6
  # Ensure we remove the container on exit
  trap 'echo "Stopping temporary ArangoDB..."; docker rm -f arango-run >/dev/null 2>&1 || true' EXIT
fi

export DATABASE_HOST DATABASE_USERNAME DATABASE_PASSWORD DATABASE_NAME
echo "Running persistence with:"
echo "  DATABASE_HOST=$DATABASE_HOST"
echo "  DATABASE_NAME=$DATABASE_NAME"

./.venv/bin/python 026_Entry_Point_NCM_Elevation_ArangoDB.py

echo "Done."
