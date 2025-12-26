#!/usr/bin/env bash
set -euo pipefail

# Test script for /mcp/resource endpoint. Sends a repo path resource payload.
URL=${1:-http://127.0.0.1:8000/mcp/resource}
SCHEMA_PATH=${2:-sample_schemas}

jq --version >/dev/null 2>&1 || echo "Warning: jq not found; raw JSON will be printed"

PAYLOAD=$(jq -n --arg path "$SCHEMA_PATH" '{resource: {type: "git:repo_path", path: $path}}')

curl -s -X POST "$URL" -H "Content-Type: application/json" -d "$PAYLOAD" | jq || true
