#!/usr/bin/env bash
set -euo pipefail

# Usage:
# MCP_AUTH=ghp_xxx ./mcp_register_space.sh
# or export MCP_AUTH and run

MCP_URL="${MCP_URL:-https://api.githubcopilot.com/mcp/}"
AUTH="${MCP_AUTH:-}"
SPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
SPACE_JSON="$SPACE_DIR/space.json"

if [ -z "$AUTH" ]; then
  echo "Provide token in MCP_AUTH environment variable. Example: MCP_AUTH=ghp_xxx $0" >&2
  exit 2
fi

if [ ! -f "$SPACE_JSON" ]; then
  echo "space.json not found in $SPACE_DIR" >&2
  exit 2
fi

echo "Attempting to register space at $MCP_URL (this may fail if the server does not accept direct registrations)"

HTTP_STATUS=$(curl -sS -o /tmp/mcp_register_resp.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $AUTH" \
  -H "Content-Type: application/json" \
  --data-binary @"$SPACE_JSON" \
  "$MCP_URL/spaces") || true

echo "HTTP status: $HTTP_STATUS"
echo "Response:"
cat /tmp/mcp_register_resp.json || true

if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
  echo "Registration request succeeded (server returned $HTTP_STATUS)."
else
  echo "Registration request failed or not supported by the server. Check response and server capabilities." >&2
fi
