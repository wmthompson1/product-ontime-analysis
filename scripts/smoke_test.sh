#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test script
# Usage: ./scripts/smoke_test.sh [BASE_URL]
# Example: ./scripts/smoke_test.sh http://localhost:8080

BASE_URL=${1:-http://localhost:8080}
TIMEOUT=5
FAILED=0

echo "Running smoke tests against: $BASE_URL"

check() {
  local path="$1"
  local name="$2"
  if curl -s --max-time $TIMEOUT -f "$BASE_URL$path" -o /dev/null; then
    echo "[OK] $name ($path)"
  else
    echo "[FAIL] $name ($path)"
    FAILED=$((FAILED+1))
  fi
}

# Mandatory: Home page must respond
check "/" "Home page"

# Optional sanity endpoints
check "/health" "Health endpoint"
check "/mcp" "MCP discovery"
check "/schema" "Schema endpoint"

# Finish
if [ "$FAILED" -eq 0 ]; then
  echo "Smoke tests passed"
  exit 0
else
  echo "Smoke tests failed: $FAILED failures"
  exit 2
fi
