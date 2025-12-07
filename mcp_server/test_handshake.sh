#!/usr/bin/env bash
set -euo pipefail

# Test script for /mcp/handshake endpoint. Reads MCP_TOKEN from env if present.
URL=${1:-http://127.0.0.1:8000/mcp/handshake}
TOKEN_VAR=${MCP_TOKEN:-}

if [ -n "$TOKEN_VAR" ]; then
  AUTH_HEADER=( -H "Authorization: Bearer $TOKEN_VAR" )
else
  AUTH_HEADER=()
fi

curl -s -X POST "$URL" -H "Content-Type: application/json" "${AUTH_HEADER[@]}" -d '{"client":"test-script","time":"'"$(date --iso-8601=seconds)"'"}' | jq || true
