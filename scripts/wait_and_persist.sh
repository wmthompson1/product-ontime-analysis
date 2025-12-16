#!/usr/bin/env bash
set -euo pipefail
# Usage: scripts/wait_and_persist.sh [graphml-path]
GRAPHML_PATH="${1:-data/schema.graphml}"
# Prefer ARANGO_* envs, fall back to older DATABASE_* names for compatibility
ARANGO_HOST="${ARANGO_URL:-${ARANGO_HOST:-${ARANGO_HOST:-http://localhost:8529}}}"
ARANGO_USER="${ARANGO_USER:-${ARANGO_USERNAME:-${ARANGO_USER:-root}}}"
ARANGO_PASS="${ARANGO_PASSWORD:-${ARANGO_ROOT_PASSWORD:-${ARANGO_PASSWORD:-example}}}"
ARANGO_DB="${ARANGO_DB:-${ARANGO_DATABASE:-${ARANGO_DB:-manufacturing_graph}}}"
CONTAINER_NAME="${ARANGO_CONTAINER_NAME:-arangodb}"
IMAGE="${DOCKER_IMAGE:-arangodb/arangodb:latest}"
WAIT_TIMEOUT=${WAIT_TIMEOUT:-60}

echo "Target Arango host: $ARANGO_HOST"
# Start container if Docker is available and container not running
if command -v docker >/dev/null 2>&1; then
  if ! docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Names}}' | grep -q "${CONTAINER_NAME}"; then
    echo "Starting Arango container..."
    docker run -e ARANGO_ROOT_PASSWORD="$ARANGO_PASS" -d --name "$CONTAINER_NAME" -p 8529:8529 "$IMAGE"
  else
    echo "Arango container already running."
  fi
else
  echo "Docker not found in this environment; ensure Arango is running at $ARANGO_HOST"
fi

# Wait for HTTP readiness
echo -n "Waiting for Arango at $ARANGO_HOST "
t=$WAIT_TIMEOUT
while ! curl -fsS "$ARANGO_HOST/_api/version" >/dev/null 2>&1 && [ $t -gt 0 ]; do
  sleep 1; t=$((t-1)); echo -n "."
done
if [ $t -le 0 ]; then
  echo; echo "Timeout waiting for Arango. Exiting."
  exit 1
fi
echo; echo "Arango ready."

# Run persist script (explicit venv python)
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python scripts/persist_to_arango.py --graphml "$GRAPHML_PATH" || {
    echo "persist script failed"
    exit 1
  }
else
  python3 scripts/persist_to_arango.py --graphml "$GRAPHML_PATH"
fi