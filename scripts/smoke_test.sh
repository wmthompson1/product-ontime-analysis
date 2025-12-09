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

# MCP: use the implemented POST endpoints instead of non-existent GETs
echo "Checking MCP handshake (POST /mcp/handshake)"
if curl -s --max-time $TIMEOUT -f -X POST -H 'Content-Type: application/json' -d '{"client":"smoke_test"}' "$BASE_URL/mcp/handshake" -o /dev/null; then
  echo "[OK] MCP handshake (POST /mcp/handshake)"
else
  echo "[FAIL] MCP handshake (POST /mcp/handshake)"
  FAILED=$((FAILED+1))
fi

echo "Checking MCP resource (POST /mcp/resource)"
if curl -s --max-time $TIMEOUT -f -X POST -H 'Content-Type: application/json' -d '{"resource":{"type":"git:repo_path","path":"mcp_server"}}' "$BASE_URL/mcp/resource" -o /dev/null; then
  echo "[OK] MCP resource (POST /mcp/resource)"
else
  echo "[FAIL] MCP resource (POST /mcp/resource)"
  FAILED=$((FAILED+1))
fi

# Finish
if [ "$FAILED" -eq 0 ]; then
  echo "Smoke tests passed"
  exit 0
else
  echo "Smoke tests failed: $FAILED failures"
  exit 2
fi
